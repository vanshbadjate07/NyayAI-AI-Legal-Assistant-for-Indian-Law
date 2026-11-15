"""OCR for user-uploaded images and PDFs.

Routing:
  * Devanagari (Hindi/Marathi) -> EasyOCR. gpu=False because EasyOCR has no
    MPS backend, and CPU mode is stable on Apple Silicon.
  * English / unknown -> the Ollama vision model (qwen3-vl:2b-instruct),
    falling back to EasyOCR when the vision model returns almost nothing.

qwen3-vl:2b-instruct replaced moondream here: moondream is English-only, so
a Hindi notice photographed by a user returned near-empty text and silently
degraded the whole answer.
"""
from functools import lru_cache

import easyocr
import ollama

from app.core.config import settings

_ollama_client = ollama.Client(host=settings.ollama_host)

OCR_PROMPT = (
    "Extract all text from this document image exactly as written, "
    "preserving line structure. Output only the extracted text, with no "
    "commentary."
)
# Below this many characters the vision model is assumed to have failed.
MIN_USABLE_CHARS = 15


@lru_cache(maxsize=1)
def get_easyocr_reader() -> easyocr.Reader:
    return easyocr.Reader(["hi", "mr", "en"], gpu=False)


def ocr_vision(image_path: str) -> str:
    try:
        response = _ollama_client.chat(
            model=settings.vision_model,
            messages=[{"role": "user", "content": OCR_PROMPT, "images": [image_path]}],
        )
    except Exception as e:
        raise RuntimeError(
            f"Vision model call failed — is '{settings.vision_model}' pulled "
            f"in Ollama ('ollama pull {settings.vision_model}') and is "
            f"'ollama serve' running? Original error: {e}"
        )
    return response["message"]["content"].strip()


def ocr_devanagari(image_path: str) -> str:
    results = get_easyocr_reader().readtext(image_path, detail=0, paragraph=True)
    return "\n".join(results).strip()


def extract_text(image_path: str, hint_language: str = "auto") -> str:
    """hint_language: 'en' | 'hi' | 'mr' | 'auto'."""
    if hint_language in ("hi", "mr"):
        return ocr_devanagari(image_path)
    if hint_language == "en":
        return ocr_vision(image_path)

    try:
        text = ocr_vision(image_path)
    except RuntimeError:
        return ocr_devanagari(image_path)

    if len(text.strip()) < MIN_USABLE_CHARS:
        text = ocr_devanagari(image_path)
    return text
