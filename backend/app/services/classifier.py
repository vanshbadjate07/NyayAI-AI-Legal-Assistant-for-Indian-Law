"""Lightweight keyword-based vertical classifier.

Keyword match is tried first because it's instant and free. If nothing
matches, falls back to the LLM for a single-word classification — handles
phrasing the keyword list doesn't anticipate (the "tackle any question"
requirement).
"""
from app.services.llm import generate

KEYWORDS = {
    "rti": [
        "rti", "right to information", "public information officer", "pio",
        "information commission", "appeal under section",
    ],
    "tenancy": [
        "rent", "tenant", "tenancy", "landlord", "lease", "eviction",
        "security deposit", "rent agreement",
    ],
    "consumer": [
        "consumer", "refund", "defective product", "warranty", "e-commerce",
        "deficiency in service", "consumer forum", "ncdrc",
    ],
    "family": [
        "divorce", "marriage", "maintenance", "domestic violence", "custody",
        "alimony", "dowry", "matrimonial",
    ],
    "criminal": [
        "fir", "police", "arrest", "bail", "ipc", "bns", "bnss", "criminal",
        "theft", "assault", "complaint against", "cognizable",
    ],
}

VALID_VERTICALS = set(KEYWORDS.keys()) | {"general"}


def _keyword_classify(question: str) -> str:
    q = question.lower()
    scores = {v: sum(1 for kw in kws if kw in q) for v, kws in KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else ""


def _llm_classify(question: str) -> str:
    prompt = (
        "Classify this legal question into exactly one category: "
        "rti, tenancy, consumer, family, criminal, or general.\n"
        f"Question: {question}\n"
        "Reply with only the category word, nothing else."
    )
    try:
        result = generate(prompt, temperature=0.0).strip().lower()
    except Exception:
        return "general"
    for v in VALID_VERTICALS:
        if v in result:
            return v
    return "general"


def classify_vertical(question: str) -> str:
    vertical = _keyword_classify(question)
    if vertical:
        return vertical
    return _llm_classify(question)
