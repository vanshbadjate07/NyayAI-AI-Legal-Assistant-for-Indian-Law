"""OCR fallback for source PDFs that have no usable text layer.

Two of the nine Acts in this knowledge base cannot be read by pypdf:

  * mh_rent_control_1999.pdf  — a 60-page scan, zero extractable text
  * rti_act_2005_hi.pdf       — a legacy non-Unicode Devanagari font, so
                                extraction returns mojibake, not Hindi

Without this fallback the Tenancy vertical has no state law in it and the
Hindi side of the knowledge base is noise. Each page is rasterised with
pdftoppm (poppler) and read with EasyOCR, and the result is cached as a
.txt file per PDF so ingestion does not pay the OCR cost again. Measured
on an M1 (CPU only): ~19 s/page for English, ~50 s/page for Devanagari.

Usage:
    python ingestion/ocr_fallback.py                 # all files needing OCR
    python ingestion/ocr_fallback.py --file <path> --langs hi mr en
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(THIS_DIR, "..", "data", "legal_docs")
CACHE_DIR = os.path.join(THIS_DIR, "ocr_cache")

# Which files need OCR, and in which languages, as established by
# validate_kb.py. English is kept alongside Hindi/Marathi because the Hindi
# RTI gazette mixes Latin numerals and English section markers.
OCR_TARGETS = {
    "mh_rent_control_1999.pdf": ["en"],
    "rti_act_2005_hi.pdf": ["hi", "mr", "en"],
}

DPI = 200  # enough for clean statute type; 300 was ~2x slower for no gain


def _require_pdftoppm() -> None:
    if shutil.which("pdftoppm") is None:
        raise RuntimeError(
            "pdftoppm not found. Install poppler:  brew install poppler  "
            "(macOS)  /  apt-get install poppler-utils  (Debian)."
        )


def cache_path(pdf_name: str) -> str:
    return os.path.join(CACHE_DIR, pdf_name.replace(".pdf", "") + ".txt")


def page_count(pdf_path: str) -> int:
    from pypdf import PdfReader
    return len(PdfReader(pdf_path).pages)


def ocr_pdf(pdf_path: str, langs, dpi: int = DPI, force: bool = False) -> str:
    """OCRs a PDF page by page and returns the full text.

    Per-page results are written to ocr_cache/<name>/page_NNN.txt as they
    complete, so an interrupted run resumes instead of starting over.
    """
    _require_pdftoppm()
    import easyocr

    name = os.path.basename(pdf_path)
    final_path = cache_path(name)
    if os.path.exists(final_path) and not force:
        print(f"[cached] {name} -> {final_path}")
        return open(final_path, encoding="utf-8").read()

    page_dir = os.path.join(CACHE_DIR, name.replace(".pdf", ""))
    os.makedirs(page_dir, exist_ok=True)

    total = page_count(pdf_path)
    print(f"[ocr] {name}: {total} pages, langs={langs}, dpi={dpi}")
    reader = easyocr.Reader(list(langs), gpu=False)  # no MPS backend in EasyOCR

    texts = []
    started = time.time()
    for page_no in range(1, total + 1):
        page_txt = os.path.join(page_dir, f"page_{page_no:03d}.txt")
        if os.path.exists(page_txt) and not force:
            texts.append(open(page_txt, encoding="utf-8").read())
            continue

        with tempfile.TemporaryDirectory() as tmp:
            prefix = os.path.join(tmp, "pg")
            subprocess.run(
                ["pdftoppm", "-r", str(dpi), "-f", str(page_no), "-l", str(page_no),
                 "-png", pdf_path, prefix],
                check=True, capture_output=True,
            )
            images = sorted(glob.glob(prefix + "*.png"))
            if not images:
                texts.append("")
                continue
            lines = reader.readtext(images[0], detail=0, paragraph=True)

        text = "\n".join(lines).strip()
        with open(page_txt, "w", encoding="utf-8") as fh:
            fh.write(text)
        texts.append(text)

        done = page_no
        rate = (time.time() - started) / max(1, done)
        print(f"  page {page_no}/{total}  {len(text)} chars  "
              f"({rate:.1f}s/page, ~{rate * (total - done) / 60:.1f} min left)",
              flush=True)

    full = "\n\n".join(texts).strip()
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(final_path, "w", encoding="utf-8") as fh:
        fh.write(full)

    dev = sum(1 for c in full if "ऀ" <= c <= "ॿ")
    print(f"[done] {name}: {len(full)} chars ({dev} Devanagari) -> {final_path}")
    return full


def load_ocr_pages(pdf_name: str) -> list:
    """Returns [{"page": 1, "text": "..."}, ...] from the per-page cache.

    Preferred over load_ocr_text(): the page number is taken from the cache
    filename, so a chunk from an OCR'd document cites the page it actually
    came from. Splitting the joined text on blank lines would drift by one
    for every page that OCR'd to nothing.
    """
    page_dir = os.path.join(CACHE_DIR, pdf_name.replace(".pdf", ""))
    if not os.path.isdir(page_dir):
        return []
    pages = []
    for path in sorted(glob.glob(os.path.join(page_dir, "page_*.txt"))):
        number = int(os.path.basename(path)[5:-4])
        with open(path, encoding="utf-8") as fh:
            pages.append({"page": number, "text": fh.read()})
    return pages


def load_ocr_text(pdf_name: str) -> str:
    """Returns cached OCR text for a PDF, or '' if it was never OCR'd.
    Used by ingest.py so ingestion never triggers a slow OCR run itself."""
    path = cache_path(pdf_name)
    return open(path, encoding="utf-8").read() if os.path.exists(path) else ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="single PDF path to OCR")
    ap.add_argument("--langs", nargs="+", default=["en"])
    ap.add_argument("--dpi", type=int, default=DPI)
    ap.add_argument("--force", action="store_true", help="ignore cached results")
    args = ap.parse_args()

    os.makedirs(CACHE_DIR, exist_ok=True)

    if args.file:
        ocr_pdf(args.file, args.langs, args.dpi, args.force)
        return 0

    summary = {}
    for pdf_name, langs in OCR_TARGETS.items():
        matches = glob.glob(os.path.join(DATA_DIR, "*", pdf_name))
        if not matches:
            print(f"[skip] {pdf_name} not found under {DATA_DIR}")
            continue
        text = ocr_pdf(matches[0], langs, args.dpi, args.force)
        summary[pdf_name] = {
            "chars": len(text),
            "devanagari": sum(1 for c in text if "ऀ" <= c <= "ॿ"),
            "langs": langs,
        }

    with open(os.path.join(CACHE_DIR, "ocr_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    print("\nOCR summary:", json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
