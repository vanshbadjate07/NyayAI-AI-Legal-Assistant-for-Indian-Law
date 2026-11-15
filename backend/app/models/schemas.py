from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=2000)
    language: Optional[str] = Field(
        None, description='"en" | "hi" | "mr" — auto-detected when omitted'
    )


class SourceChunk(BaseModel):
    """One retrieved chunk, returned so the user can see the evidence the
    answer was generated from."""
    text: str
    source: str
    act: Optional[str] = None
    section: Optional[str] = None
    section_title: Optional[str] = None
    page: Optional[int] = None
    score: float


class Grounding(BaseModel):
    sections_cited: List[str] = []
    sections_in_context: List[str] = []
    unsupported_sections: List[str] = []
    grounded: bool = True


class QueryResponse(BaseModel):
    answer: str
    vertical: str
    language: str
    sources: List[SourceChunk]
    abstained: bool = False
    grounding: Optional[Grounding] = None
    warning: Optional[str] = None
    diagnostics: Optional[Dict[str, Any]] = None
    disclaimer: Optional[str] = None


class UploadResponse(BaseModel):
    extracted_text: str
    detected_language: str
    answer: Optional[str] = None
    vertical: Optional[str] = None
    sources: Optional[List[SourceChunk]] = None
    abstained: Optional[bool] = None
    grounding: Optional[Grounding] = None
    warning: Optional[str] = None
    disclaimer: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    knowledge_base_chunks: int = 0
    collection: Optional[str] = None
    embedding_model: Optional[str] = None
    llm_model: Optional[str] = None
    llm_reachable: Optional[bool] = None
    acts_indexed: Optional[int] = None
    verticals: Optional[Dict[str, int]] = None
    detail: Optional[str] = None
