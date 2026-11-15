import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import QueryLog
from app.models.schemas import QueryRequest, QueryResponse
from app.services import rag

router = APIRouter()


def _log(db: Session, req: QueryRequest, result: dict, source_type: str = "text") -> None:
    """Persists every query and its answer to SQLite. Kept non-fatal: a
    logging failure must never cost the user their answer."""
    try:
        db.add(QueryLog(
            question=req.question,
            language=result.get("language"),
            vertical=result.get("vertical"),
            answer=result.get("answer"),
            sources=json.dumps(result.get("sources", []), ensure_ascii=False),
            source_type=source_type,
        ))
        db.commit()
    except Exception:
        db.rollback()


@router.post("/query", response_model=QueryResponse)
def query(req: QueryRequest, db: Session = Depends(get_db)):
    try:
        result = rag.answer_question(req.question, req.language)
    except RuntimeError as e:
        # Expected, actionable failures: empty knowledge base, Ollama down.
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

    _log(db, req, result)
    return result
