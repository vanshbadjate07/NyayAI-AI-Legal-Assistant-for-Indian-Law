"""Health endpoint — reports what is actually loaded, not just HTTP 200.

The frontend uses this to show an "offline" badge, and it is the quickest
way to confirm after a fresh clone that the vector store was built and
Ollama is reachable.
"""
import ollama
from fastapi import APIRouter

from app.core.config import settings
from app.models.schemas import HealthResponse
from app.services import vectorstore

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health():
    try:
        collection = vectorstore.get_collection()
        total = collection.count()
    except Exception as e:
        return HealthResponse(status="degraded", detail=f"vector store error: {e}")

    per_vertical = {}
    acts = set()
    if total:
        try:
            sample = collection.get(include=["metadatas"], limit=10000)
            for meta in sample.get("metadatas") or []:
                if not meta:
                    continue
                v = meta.get("vertical", "unknown")
                per_vertical[v] = per_vertical.get(v, 0) + 1
                if meta.get("act"):
                    acts.add(meta["act"])
        except Exception:
            pass

    llm_ok = None
    try:
        ollama.Client(host=settings.ollama_host).list()
        llm_ok = True
    except Exception:
        llm_ok = False

    return HealthResponse(
        status="ok" if total and llm_ok else "degraded",
        knowledge_base_chunks=total,
        collection=settings.chroma_collection,
        embedding_model=settings.embed_model,
        llm_model=settings.llm_model,
        llm_reachable=llm_ok,
        acts_indexed=len(acts),
        verticals=per_vertical,
        detail=None if total and llm_ok else (
            "knowledge base empty — run ingestion/ingest.py" if not total
            else "Ollama not reachable — run 'ollama serve'"
        ),
    )
