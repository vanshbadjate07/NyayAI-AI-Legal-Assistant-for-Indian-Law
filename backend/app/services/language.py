from langdetect import detect, DetectorFactory

DetectorFactory.seed = 0

SUPPORTED = {"en": "English", "hi": "Hindi", "mr": "Marathi"}
LANG_NAMES_FOR_PROMPT = {
    "en": "English",
    "hi": "Hindi (Devanagari script)",
    "mr": "Marathi (Devanagari script)",
}


def detect_language(text: str) -> str:
    """Best-effort language detection, defaults to English on any failure
    or unsupported language (e.g. OCR noise)."""
    text = (text or "").strip()
    if not text:
        return "en"
    try:
        lang = detect(text)
        if lang in SUPPORTED:
            return lang
        return "en"
    except Exception:
        return "en"
