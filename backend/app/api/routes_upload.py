import os
import shutil
import tempfile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.models.schemas import UploadResponse
from app.services import language, ocr, rag

router = APIRouter()

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}


@router.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...), ask: bool = Form(True)):
    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        try:
            text = ocr.extract_text(tmp_path)
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e))

        lang = language.detect_language(text)
        result = {"extracted_text": text, "detected_language": lang}

        if ask and text.strip():
            try:
                rag_result = rag.answer_question(text, lang)
                result.update({
                    "answer": rag_result["answer"],
                    "vertical": rag_result["vertical"],
                    "sources": rag_result["sources"],
                    "abstained": rag_result.get("abstained"),
                    "grounding": rag_result.get("grounding"),
                    "warning": rag_result.get("warning"),
                    "disclaimer": rag_result.get("disclaimer"),
                })
            except RuntimeError as e:
                # OCR succeeded but RAG/KB failed — still return extracted text.
                result["answer"] = f"(Could not generate answer: {e})"

        return result
    finally:
        os.unlink(tmp_path)
