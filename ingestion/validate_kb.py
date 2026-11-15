"""Knowledge-base validator — run before ingestion.

Exists because two of the nine source PDFs in this project were silently
broken for weeks: one was an HTML 404 page saved with a .pdf extension,
and one was a scanned document with no text layer at all. Both were
indexed as "fine" and produced zero usable chunks. A download that
returns 200 is not a document, so every file is now checked for:

    1. a real PDF header (not HTML)
    2. a readable page tree
    3. an extractable text layer of meaningful size
    4. script content, so Devanagari files that extract as mojibake
       (legacy non-Unicode fonts) are caught

Usage:
    python ingestion/validate_kb.py
Exit code 1 if any file is unusable, so it can gate CI or a build step.
"""
import glob
import json
import os
import re
import sys

from pypdf import PdfReader

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(THIS_DIR, "..", "data", "legal_docs")

# Below this many extracted characters per page, a PDF is treated as having
# no usable text layer (i.e. it is a scan and needs the OCR fallback).
MIN_CHARS_PER_PAGE = 200
# A file whose name says it is Hindi/Marathi must actually contain
# Devanagari; below this share of letters we assume a broken font encoding.
MIN_DEVANAGARI_RATIO = 0.30


def devanagari_ratio(text: str) -> float:
    letters = sum(1 for c in text if c.isalpha())
    if not letters:
        return 0.0
    dev = sum(1 for c in text if "ऀ" <= c <= "ॿ")
    return dev / letters


def inspect(path: str) -> dict:
    name = os.path.basename(path)
    rec = {
        "file": name,
        "vertical": os.path.basename(os.path.dirname(path)),
        "size_kb": round(os.path.getsize(path) / 1024, 1),
        "pages": 0,
        "chars": 0,
        "chars_per_page": 0.0,
        "devanagari_ratio": 0.0,
        "status": "ok",
        "problem": "",
    }

    with open(path, "rb") as fh:
        header = fh.read(5)
    if header != b"%PDF-":
        rec["status"] = "broken"
        rec["problem"] = "not a PDF (likely an HTML error page saved as .pdf)"
        return rec

    try:
        reader = PdfReader(path)
        pages = reader.pages
        rec["pages"] = len(pages)
    except Exception as e:
        rec["status"] = "broken"
        rec["problem"] = f"unreadable page tree: {type(e).__name__}"
        return rec

    text_parts = []
    for page in pages:
        try:
            text_parts.append(page.extract_text() or "")
        except Exception:
            text_parts.append("")
    text = re.sub(r"\s+", " ", " ".join(text_parts))

    rec["chars"] = len(text)
    rec["chars_per_page"] = round(len(text) / max(1, rec["pages"]), 1)
    rec["devanagari_ratio"] = round(devanagari_ratio(text), 3)

    if rec["chars_per_page"] < MIN_CHARS_PER_PAGE:
        rec["status"] = "no_text_layer"
        rec["problem"] = "scanned PDF — needs the OCR fallback in ingest.py"
    elif re.search(r"_(hi|mr)\b|_(hi|mr)\.pdf$", name) and rec["devanagari_ratio"] < MIN_DEVANAGARI_RATIO:
        rec["status"] = "bad_encoding"
        rec["problem"] = (
            "named as Devanagari but extracts almost no Devanagari — "
            "legacy non-Unicode font; needs the OCR fallback"
        )
    return rec


def main() -> int:
    paths = sorted(glob.glob(os.path.join(DATA_DIR, "*", "*.pdf")))
    if not paths:
        print(f"No PDFs found under {DATA_DIR}")
        return 1

    records = [inspect(p) for p in paths]

    header = f"{'file':<34}{'vert':<10}{'pages':>6}{'chars':>9}{'c/page':>8}{'dev%':>6}  status"
    print(header)
    print("-" * len(header))
    for r in records:
        print(
            f"{r['file']:<34}{r['vertical']:<10}{r['pages']:>6}{r['chars']:>9}"
            f"{r['chars_per_page']:>8.0f}{r['devanagari_ratio'] * 100:>6.0f}  {r['status']}"
            + (f" — {r['problem']}" if r["problem"] else "")
        )

    out = os.path.join(THIS_DIR, "kb_validation.json")
    with open(out, "w") as fh:
        json.dump(records, fh, indent=2, ensure_ascii=False)

    ok = sum(1 for r in records if r["status"] == "ok")
    needs_ocr = [r for r in records if r["status"] in ("no_text_layer", "bad_encoding")]
    broken = [r for r in records if r["status"] == "broken"]

    print(f"\n{ok}/{len(records)} usable directly, {len(needs_ocr)} need OCR, {len(broken)} broken.")
    print(f"Report written to {out}")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
