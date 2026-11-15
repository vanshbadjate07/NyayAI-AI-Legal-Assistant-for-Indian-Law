"""Document processing for the NyayAI knowledge base.

Per PDF the pipeline is:

    extract_pdf_text()   raw text, one entry per page
    clean_page()         drop page furniture, de-hyphenate, unwrap lines
    build_document()     one flowing text + a character-offset -> page map
    find_section_markers()  locate every statutory section heading
    chunk_document()     section-aligned chunks, each carrying its metadata

Two things drove this design, both learned from the actual PDFs:

1. These government PDFs extract with a hard line break every ~90
   characters, not at paragraph ends. Splitting on blank lines therefore
   produces one "paragraph" per page, so lines are unwrapped into flowing
   text first.

2. A legal answer is only useful if it can be traced to a section of an
   Act. Section headings appear inline in the extracted stream
   ("5. Designation of Public Information Officers.-(1) Every..."), so
   their character offsets are found up front; chunks are then started at
   those offsets where possible and every chunk inherits the last heading
   that precedes it. A chunk holding only the tail of a long section is
   still correctly labelled.
"""
import re
from typing import Dict, List, Optional, Tuple

from pypdf import PdfReader

# ~900 characters is about 200-260 tokens of English legal prose: specific
# enough that a top-5 retrieval stays on one provision, long enough that a
# sub-clause keeps the sentence that governs it. Well inside bge-m3's
# 8192-token input limit.
CHUNK_SIZE = 900
# 180 characters (20%) of overlap, so a provision that straddles a chunk
# boundary is complete in at least one chunk.
CHUNK_OVERLAP = 180
# Chunks shorter than this are index noise (stray headers, page numbers).
MIN_CHUNK_CHARS = 120

# Section numbers in the indexed Acts run up to 531 (BNSS, 2023).
_MAX_SECTION_NUMBER = 600

# A heading in the extracted stream: start of text, or after a sentence
# end / bracket, then "<number>." then a capital letter or a bracket.
_SECTION_MARKER = re.compile(
    r"(?:(?<=[.;:\]\)])\s|\A|(?<=\n))(\d{1,3}[A-Z]?)\s*\.\s*(?=[A-Z\[(ऀ-ॿ])"
)
# The human-readable title that follows a heading, where there is one
# ("Short title, extent and commencement." / "Judicial separation .—").
_SECTION_TITLE = re.compile(r"\A\s*([A-Z][A-Za-z0-9 ,\-\(\)'’/]{3,90}?)\s*\.?\s*[-—–—\[(]")
_INLINE_SECTION = re.compile(r"(?:Section|SECTION|Sec\.)\s*(\d{1,3}[A-Z]?)|(?:धारा|कलम)\s*(\d{1,3})")
_CHAPTER = re.compile(r"CHAPTER\s+([IVXLC]+|\d{1,2})\b", re.IGNORECASE)

# Running headers/footers these PDFs repeat on every page, plus bare page
# numbers. Dropped so they are not embedded hundreds of times over.
_FURNITURE = [
    re.compile(r"^\s*\d{1,4}\s*$"),
    re.compile(r"^\s*page\s+\d+\s*(of\s+\d+)?\s*$", re.IGNORECASE),
    re.compile(r"^\s*-+\s*\d+\s*-+\s*$"),
    re.compile(r"^\s*SEC\.\s*\d+\]\s*THE GAZETTE OF INDIA.*$", re.IGNORECASE),
    re.compile(r"^\s*THE GAZETTE OF INDIA EXTRAORDINARY\s*\d*\s*$", re.IGNORECASE),
    re.compile(r"^\s*Right to Information Act,\s*2005\s*$", re.IGNORECASE),
    re.compile(r"^\s*\(?Chapter\s+[IVXLC]+\s*[-—–].*\)?\s*$", re.IGNORECASE),
]


def extract_pdf_text(path: str) -> List[Dict]:
    """Returns [{"page": 1, "text": "..."}, ...], one entry per page.

    pypdf is used because the usable Acts in this knowledge base are
    born-digital PDFs with a real text layer. Files that come back
    effectively empty are scans; ingest.py routes those to the OCR
    fallback rather than indexing nothing.
    """
    reader = PdfReader(path)
    pages = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        pages.append({"page": i + 1, "text": text})
    return pages


def clean_page(text: str) -> str:
    """Removes page furniture, repairs hyphenated line breaks and unwraps
    hard-wrapped lines into flowing text."""
    if not text:
        return ""

    # "informa-\ntion" -> "information" (PDF line-break hyphenation).
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)

    kept = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped or any(p.match(stripped) for p in _FURNITURE):
            continue
        kept.append(stripped)

    # Lines are wrapped mid-sentence, so join with a single space.
    joined = " ".join(kept)
    # pypdf inserts stray spaces inside words ("sub -section" / "applic ation").
    joined = re.sub(r"(\w)\s+-\s*(\w)", r"\1-\2", joined)
    joined = re.sub(r"[ \t ]{2,}", " ", joined)
    return joined.strip()


def build_document(pages: List[Dict]) -> Dict:
    """Concatenates cleaned pages into one text and records which character
    range came from which page, so every chunk can cite a page number."""
    parts: List[str] = []
    spans: List[Tuple[int, int, int]] = []
    cursor = 0
    for page in pages:
        cleaned = clean_page(page.get("text", ""))
        if not cleaned:
            continue
        parts.append(cleaned)
        spans.append((cursor, cursor + len(cleaned), page["page"]))
        cursor += len(cleaned) + 1
    return {"text": " ".join(parts), "page_spans": spans}


def page_at(spans: List[Tuple[int, int, int]], index: int) -> Optional[int]:
    for start, end, page in spans:
        if start <= index <= end:
            return page
    return spans[-1][2] if spans else None


def find_section_markers(text: str) -> List[Dict]:
    """Returns [{"index": int, "section": "Section 7", "title": str}, ...]
    for every statutory heading found, in document order."""
    markers = []
    for m in _SECTION_MARKER.finditer(text):
        raw = m.group(1)
        try:
            if int(re.sub(r"[A-Z]", "", raw)) > _MAX_SECTION_NUMBER:
                continue
        except ValueError:
            continue
        tail = text[m.end():m.end() + 120]
        title_match = _SECTION_TITLE.match(tail)
        markers.append({
            "index": m.start(),
            "section": f"Section {raw}",
            "title": title_match.group(1).strip() if title_match else "",
        })
    return markers


def find_chapter_markers(text: str) -> List[Dict]:
    return [
        {"index": m.start(), "chapter": f"Chapter {m.group(1).upper()}"}
        for m in _CHAPTER.finditer(text)
    ]


def _label_at(markers: List[Dict], index: int, key: str, default: str = "") -> str:
    """Last marker at or before `index` — how a chunk inherits the section
    it sits inside even when the heading is in an earlier chunk."""
    label = default
    for m in markers:
        if m["index"] <= index:
            label = m[key]
        else:
            break
    return label


def _word_boundary_end(text: str, start: int, size: int) -> int:
    """Chunk end, pulled back to the nearest sentence or word boundary so
    chunks do not stop mid-word."""
    hard_end = min(len(text), start + size)
    if hard_end >= len(text):
        return len(text)
    window = text[start:hard_end]
    for pattern in (". ", "; ", " "):
        cut = window.rfind(pattern)
        if cut > size * 0.5:
            return start + cut + len(pattern) - 1
    return hard_end


def chunk_document(
    doc: Dict,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> List[Dict]:
    """Splits a built document into overlapping, section-aligned chunks.

    Chunk boundaries prefer the start of the next section: a chunk is cut
    short when a new heading falls inside it, so provisions from two
    different sections rarely share a chunk.
    """
    text = doc["text"]
    spans = doc["page_spans"]
    if not text:
        return []

    sections = find_section_markers(text)
    chapters = find_chapter_markers(text)
    section_starts = [m["index"] for m in sections]

    chunks: List[Dict] = []
    start = 0
    while start < len(text):
        # Where does the next section begin, far enough ahead to be worth
        # cutting for? Scanning forward keeps the loop monotonic.
        next_section = next(
            (s for s in section_starts if s > start + MIN_CHUNK_CHARS), None
        )
        end = _word_boundary_end(text, start, chunk_size)

        cut_at_section = False
        if next_section is not None and next_section < end:
            end = next_section
            cut_at_section = True

        body = text[start:end].strip()
        if len(body) >= MIN_CHUNK_CHARS:
            section = _label_at(sections, start, "section", "N/A")
            title = _label_at(sections, start, "title", "")
            if section == "N/A":
                inline = _INLINE_SECTION.search(body)
                if inline:
                    section = f"Section {inline.group(1) or inline.group(2)}"
            chunks.append({
                "text": body,
                "page_start": page_at(spans, start),
                "page_end": page_at(spans, max(start, end - 1)),
                "section": section,
                "section_title": title,
                "chapter": _label_at(chapters, start, "chapter", ""),
                "char_start": start,
            })

        if end >= len(text):
            break
        # A section boundary is a clean semantic break, so no overlap is
        # carried across it; inside a long section, overlap is applied so a
        # provision split across chunks stays readable in one of them.
        if cut_at_section:
            start = end
        else:
            # Step back by the overlap, then forward to the next word
            # boundary so the carried-over text does not begin mid-word.
            back = max(end - overlap, start + 1)
            space = text.find(" ", back)
            start = space + 1 if 0 <= space < back + 40 else back

    return chunks


def chunk_pdf(path: str) -> List[Dict]:
    """Convenience wrapper: PDF path -> list of chunk dicts."""
    return chunk_document(build_document(extract_pdf_text(path)))


# ---------------------------------------------------------------------------
# Kept so older scripts/tests importing chunk_text() and detect_section()
# keep working. New code should use chunk_document().
# ---------------------------------------------------------------------------
def detect_section(text: str) -> str:
    markers = find_section_markers(text)
    if markers:
        return markers[0]["section"]
    inline = _INLINE_SECTION.search(text)
    return f"Section {inline.group(1) or inline.group(2)}" if inline else "N/A"


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    doc = {"text": clean_page(text), "page_spans": [(0, len(text), 1)]}
    return [c["text"] for c in chunk_document(doc, chunk_size, overlap)]
