"""Retrieval-only endpoint.

Returns the chunks a question retrieves without calling the LLM. It exists
for two reasons: it makes the retrieval stage inspectable on its own (the
answer is no better than what comes back here), and it is what the
evaluation harness scores retrieval quality against.
"""
from fastapi import APIRouter, HTTPException

from app.models.schemas import QueryRequest
from app.services import classifier, retrieval

router = APIRouter()


@router.post("/retrieve")
def retrieve_only(req: QueryRequest):
    try:
        vertical = classifier.classify_vertical(req.question)
        result = retrieval.retrieve(req.question, vertical)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    return {
        "question": req.question,
        "vertical": vertical,
        "diagnostics": result["diagnostics"],
        "chunks": [
            {
                "rank": i + 1,
                "score": h["score"],
                "act": h["metadata"].get("act"),
                "section": h["metadata"].get("section"),
                "section_title": h["metadata"].get("section_title"),
                "page": h["metadata"].get("page_start"),
                "source": h["metadata"].get("source"),
                "text": h["text"],
            }
            for i, h in enumerate(result["hits"])
        ],
    }
