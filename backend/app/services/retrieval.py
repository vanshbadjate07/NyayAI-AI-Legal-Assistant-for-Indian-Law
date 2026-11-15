"""Retrieval strategy — the layer between a user's question and the chunks
that are handed to the LLM.

Plain top-k over the whole collection was not good enough, for three
reasons found while testing this knowledge base:

1. **Wrong-domain matches.** "maintenance" appears in tenancy law (repairs)
   and in family law (spousal maintenance). Filtering by the classified
   vertical fixes most of it.

2. **A misclassified question returns nothing useful.** So the filter is
   not trusted blindly: if the filtered search comes back weak, the search
   is retried across the whole collection and the better result wins.

3. **Overlapping chunks crowd each other out.** Consecutive chunks share
   180 characters of overlap, so an unfiltered top-5 was often five
   near-identical windows of one section. At most
   `settings.max_chunks_per_section` (2) hits are kept per (source, section),
   so the context covers distinct provisions while still allowing a long
   section to contribute the two chunks it needs to make sense.

Finally, retrieval can abstain: if the best similarity is below
`settings.min_similarity`, the question is treated as outside the
knowledge base and no answer is generated. That is what stops the model
from inventing law for "how do I get a US visa?".
"""
from typing import Dict, List, Optional

from app.core.config import settings
from app.services import embeddings, vectorstore


def _dedupe_by_section(hits: List[Dict], per_section: int = 1) -> List[Dict]:
    """Keeps at most `per_section` chunks per (source, section) pair,
    preserving score order."""
    seen: Dict[tuple, int] = {}
    kept = []
    for hit in hits:
        meta = hit["metadata"]
        key = (meta.get("source"), meta.get("section"))
        if seen.get(key, 0) >= per_section:
            continue
        seen[key] = seen.get(key, 0) + 1
        kept.append(hit)
    return kept


def retrieve(question: str, vertical: Optional[str] = None) -> Dict:
    """Runs the retrieval pipeline for one question.

    Returns a dict with the chosen `hits` and a `diagnostics` block, which
    the API exposes so the retrieval step is inspectable rather than a
    black box (and so the evaluation harness can score it).
    """
    if vectorstore.collection_is_empty():
        raise RuntimeError(
            "Knowledge base is empty — run 'python ingestion/ingest.py' "
            "before querying."
        )

    query_vec = embeddings.embed_query(question)
    fetch_k = settings.fetch_k
    top_k = settings.top_k

    filter_used = vertical if vertical and vertical != "general" else None
    hits = vectorstore.search(query_vec, n_results=fetch_k, vertical_filter=filter_used)
    best_filtered = hits[0]["score"] if hits else 0.0

    # Fall back to the whole collection when the vertical filter looks like
    # it hurt — either the classifier was wrong or the answer genuinely
    # lives in another Act.
    fallback_used = False
    if filter_used and best_filtered < settings.fallback_similarity:
        unfiltered = vectorstore.search(query_vec, n_results=fetch_k, vertical_filter=None)
        if unfiltered and (not hits or unfiltered[0]["score"] > best_filtered):
            hits = unfiltered
            fallback_used = True

    deduped = _dedupe_by_section(hits, settings.max_chunks_per_section)[:top_k]
    top_score = deduped[0]["score"] if deduped else 0.0
    abstain = top_score < settings.min_similarity

    return {
        "hits": [] if abstain else deduped,
        "diagnostics": {
            "classified_vertical": vertical,
            "vertical_filter_applied": filter_used,
            "fallback_to_full_collection": fallback_used,
            "candidates_fetched": len(hits),
            "chunks_used": 0 if abstain else len(deduped),
            "top_similarity": top_score,
            "min_similarity_threshold": settings.min_similarity,
            "abstained": abstain,
            "collection_size": vectorstore.count(),
        },
    }
