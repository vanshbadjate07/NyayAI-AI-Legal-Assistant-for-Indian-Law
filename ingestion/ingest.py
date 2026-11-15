"""Builds the NyayAI Chroma vector store from the Acts in data/legal_docs/.

Safe to re-run: the collection is dropped and rebuilt, so there is no
duplicate-chunk drift between runs.

Pipeline per file:
    1. text layer via pypdf (chunking.extract_pdf_text)
    2. if the text layer is missing or mojibake, cached OCR text instead
       (ocr_fallback.load_ocr_text — run ocr_fallback.py first)
    3. clean -> section-aware chunks (chunking.chunk_document)
    4. attach citation metadata from ACT_REGISTRY
    5. embed with BAAI/bge-m3 and add to Chroma in batches

Usage:
    python ingestion/validate_kb.py      # check the source PDFs first
    python ingestion/ocr_fallback.py     # one-off, for the two scanned files
    python ingestion/ingest.py           # build the index
    python ingestion/ingest.py --limit 20   # quick smoke test
"""
import argparse
import json
import os
import sys
import time

import chromadb
from sentence_transformers import SentenceTransformer

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, THIS_DIR)

from chunking import build_document, chunk_document, extract_pdf_text  # noqa: E402
from ocr_fallback import load_ocr_pages, load_ocr_text  # noqa: E402

DATA_DIR = os.path.join(THIS_DIR, "..", "data", "legal_docs")
CHROMA_DIR = os.path.join(THIS_DIR, "chroma_store")
COLLECTION_NAME = "nyayai_legal_kb"
EMBED_MODEL = "BAAI/bge-m3"
STATS_PATH = os.path.join(THIS_DIR, "ingestion_stats.json")

VERTICALS = ["rti", "tenancy", "consumer", "family", "criminal"]

# Citation metadata. The filename alone is a poor citation ("per
# bns_2023.pdf" means nothing to a citizen), so every chunk carries the
# Act's real title, year and jurisdiction, and the UI cites that instead.
ACT_REGISTRY = {
    "rti_act_2005_en.pdf": {
        "act": "The Right to Information Act, 2005",
        "year": 2005, "jurisdiction": "India (Central)", "doc_language": "en",
        "source": "https://cic.gov.in/sites/default/files/RTI-Act_English.pdf",
    },
    "rti_act_2005_hi.pdf": {
        "act": "सूचना का अधिकार अधिनियम, 2005 (RTI Act, Hindi)",
        "year": 2005, "jurisdiction": "India (Central)", "doc_language": "hi",
        "source": "https://rti.gov.in/",
    },
    "model_tenancy_act_2021.pdf": {
        "act": "The Model Tenancy Act, 2021",
        "year": 2021, "jurisdiction": "India (Central model law)", "doc_language": "en",
        "source": "https://livelaw.in/pdf_upload/model-tenancy-act-394449.pdf",
    },
    "mh_rent_control_1999.pdf": {
        "act": "The Maharashtra Rent Control Act, 1999",
        "year": 1999, "jurisdiction": "Maharashtra (State)", "doc_language": "en",
        "source": "Maharashtra Government Gazette, Part IV (scanned copy)",
    },
    "cpa_2019.pdf": {
        "act": "The Consumer Protection Act, 2019",
        "year": 2019, "jurisdiction": "India (Central)", "doc_language": "en",
        "source": "https://egazette.nic.in/",
    },
    "hindu_marriage_act_1955.pdf": {
        "act": "The Hindu Marriage Act, 1955",
        "year": 1955, "jurisdiction": "India (Central)", "doc_language": "en",
        "source": "https://www.indiacode.nic.in/",
    },
    "dv_act_2005.pdf": {
        "act": "The Protection of Women from Domestic Violence Act, 2005",
        "year": 2005, "jurisdiction": "India (Central)", "doc_language": "en",
        "source": "https://www.indiacode.nic.in/",
    },
    "bns_2023.pdf": {
        "act": "The Bharatiya Nyaya Sanhita, 2023",
        "year": 2023, "jurisdiction": "India (Central)", "doc_language": "en",
        "source": "https://www.mha.gov.in/",
    },
    "bnss_2023.pdf": {
        "act": "The Bharatiya Nagarik Suraksha Sanhita, 2023",
        "year": 2023, "jurisdiction": "India (Central)", "doc_language": "en",
        "source": "https://www.mha.gov.in/",
    },
}

# Files whose text layer is unusable; ingestion reads their cached OCR text.
OCR_ONLY = {"mh_rent_control_1999.pdf", "rti_act_2005_hi.pdf"}

# Below this many characters, a text layer is treated as absent.
MIN_USABLE_CHARS = 1000
BATCH_SIZE = 32  # keeps peak RAM modest on an 8GB machine


def document_for(path: str, fname: str) -> tuple:
    """Returns (document_dict, text_source) where text_source is
    'pdf_text_layer' or 'ocr'."""
    if fname in OCR_ONLY:
        # Per-page cache files carry the true page number in their filename,
        # so citations from OCR'd documents point at the right page.
        pages = [p for p in load_ocr_pages(fname) if p["text"].strip()]
        if pages:
            return build_document(pages), "ocr"
        print(f"  [warn] {fname} needs OCR but no cached text found — "
              f"run: python ingestion/ocr_fallback.py")
        return {"text": "", "page_spans": []}, "missing_ocr"

    doc = build_document(extract_pdf_text(path))
    if len(doc["text"]) < MIN_USABLE_CHARS:
        pages = [p for p in load_ocr_pages(fname) if p["text"].strip()]
        if pages:
            return build_document(pages), "ocr"
        return doc, "empty"
    return doc, "pdf_text_layer"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0,
                    help="index only the first N chunks per file (smoke test)")
    args = ap.parse_args()

    print(f"Loading embedding model ({EMBED_MODEL}) — first run downloads ~2.2GB.")
    t0 = time.time()
    embedder = SentenceTransformer(EMBED_MODEL)
    print(f"Model loaded in {time.time() - t0:.1f}s")

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        client.delete_collection(COLLECTION_NAME)
        print("Cleared existing collection for a clean rebuild.")
    except Exception:
        pass
    collection = client.create_collection(
        name=COLLECTION_NAME,
        # Cosine similarity, because bge-m3 embeddings are L2-normalised and
        # cosine is what the model was trained to optimise.
        metadata={"hnsw:space": "cosine"},
    )

    stats = {"embedding_model": EMBED_MODEL, "collection": COLLECTION_NAME,
             "chunk_size": 900, "chunk_overlap": 180, "files": [], "total_chunks": 0}
    started = time.time()

    for vertical in VERTICALS:
        folder = os.path.join(DATA_DIR, vertical)
        if not os.path.isdir(folder):
            print(f"  [skip] no folder for '{vertical}'")
            continue

        for fname in sorted(f for f in os.listdir(folder) if f.lower().endswith(".pdf")):
            path = os.path.join(folder, fname)
            print(f"\nProcessing {vertical}/{fname}")
            try:
                doc, text_source = document_for(path, fname)
            except Exception as e:
                print(f"  [error] {fname}: {type(e).__name__}: {e}")
                stats["files"].append({"file": fname, "vertical": vertical,
                                       "chunks": 0, "error": str(e)})
                continue

            chunks = chunk_document(doc)
            if args.limit:
                chunks = chunks[:args.limit]
            if not chunks:
                print(f"  [warn] 0 chunks from {fname} (source={text_source})")
                stats["files"].append({"file": fname, "vertical": vertical,
                                       "chunks": 0, "text_source": text_source})
                continue

            meta_base = ACT_REGISTRY.get(fname, {})
            ids, docs, metas = [], [], []
            for i, ch in enumerate(chunks):
                ids.append(f"{vertical}__{fname}__{i:05d}")
                docs.append(ch["text"])
                metas.append({
                    "vertical": vertical,
                    "source": fname,
                    "act": meta_base.get("act", fname),
                    "year": meta_base.get("year", 0),
                    "jurisdiction": meta_base.get("jurisdiction", "India"),
                    "doc_language": meta_base.get("doc_language", "en"),
                    "section": ch["section"],
                    "section_title": ch["section_title"],
                    "chapter": ch["chapter"],
                    "page_start": ch["page_start"] or 0,
                    "page_end": ch["page_end"] or 0,
                    "text_source": text_source,
                    "chars": len(ch["text"]),
                })

            for i in range(0, len(docs), BATCH_SIZE):
                batch = docs[i:i + BATCH_SIZE]
                embeddings = embedder.encode(
                    batch, normalize_embeddings=True, show_progress_bar=False
                ).tolist()
                collection.add(
                    ids=ids[i:i + BATCH_SIZE],
                    documents=batch,
                    metadatas=metas[i:i + BATCH_SIZE],
                    embeddings=embeddings,
                )
                done = min(i + BATCH_SIZE, len(docs))
                print(f"  embedded {done}/{len(docs)}", end="\r", flush=True)

            labelled = sum(1 for c in chunks if c["section"] != "N/A")
            print(f"  -> {len(docs)} chunks indexed "
                  f"({labelled * 100 // len(chunks)}% with a section label, "
                  f"source={text_source})")
            stats["files"].append({
                "file": fname, "vertical": vertical,
                "act": meta_base.get("act", fname),
                "chunks": len(docs), "text_source": text_source,
                "section_labelled_pct": labelled * 100 // len(chunks),
                "avg_chars": sum(len(c["text"]) for c in chunks) // len(chunks),
            })
            stats["total_chunks"] += len(docs)

    stats["build_seconds"] = round(time.time() - started, 1)
    stats["built_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(STATS_PATH, "w") as fh:
        json.dump(stats, fh, indent=2, ensure_ascii=False)

    print(f"\nDone in {stats['build_seconds']}s. "
          f"Total chunks indexed: {stats['total_chunks']}")
    print(f"Chroma store: {CHROMA_DIR}")
    print(f"Stats written to: {STATS_PATH}")
    if stats["total_chunks"] == 0:
        print("WARNING: 0 chunks indexed — check data/legal_docs/<vertical>/")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
