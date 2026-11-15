"""Chroma vector store access and the similarity-search layer.

The collection is built by ingestion/ingest.py with cosine distance, so a
Chroma `distance` of d corresponds to a cosine similarity of 1 - d for the
L2-normalised bge-m3 vectors used here.
"""
from functools import lru_cache
from typing import Dict, List, Optional

import chromadb

from app.core.config import settings

VERTICALS = ["rti", "tenancy", "consumer", "family", "criminal"]


@lru_cache(maxsize=1)
def get_client() -> chromadb.ClientAPI:
    return chromadb.PersistentClient(path=settings.chroma_dir)


@lru_cache(maxsize=1)
def get_collection():
    return get_client().get_or_create_collection(
        name=settings.chroma_collection,
        metadata={"hnsw:space": "cosine"},
    )


def collection_is_empty() -> bool:
    return get_collection().count() == 0


def count() -> int:
    return get_collection().count()


def search(
    query_embedding: List[float],
    n_results: int = 15,
    vertical_filter: Optional[str] = None,
) -> List[Dict]:
    """Returns a flat list of hits, each with text, metadata and a cosine
    similarity score in [0, 1] — higher is more similar.

    Chroma is asked for more candidates than are finally shown, because the
    retrieval layer in rag.py then de-duplicates by section and keeps the
    best few. Over-fetching is cheap (HNSW) and raises the chance that the
    five chunks actually handed to the LLM cover distinct provisions.
    """
    collection = get_collection()
    where = {"vertical": vertical_filter} if vertical_filter else None

    raw = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, max(1, collection.count())),
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    docs = (raw.get("documents") or [[]])[0]
    metas = (raw.get("metadatas") or [[]])[0]
    dists = (raw.get("distances") or [[]])[0]

    hits = []
    for doc, meta, dist in zip(docs, metas, dists):
        similarity = 1.0 - float(dist) if dist is not None else 0.0
        hits.append({
            "text": doc,
            "metadata": meta or {},
            "score": round(max(0.0, min(1.0, similarity)), 4),
        })
    return hits
