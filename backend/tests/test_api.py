"""API and unit tests for NyayAI.

Run from the repository root (or from backend/):

    backend/venv/bin/python -m pytest backend/tests -v

No server needs to be running: FastAPI's TestClient calls the app
in-process. Tests that would otherwise require Ollama or a built vector
store patch those boundaries, so the suite passes on a clean checkout
before ingestion has been run.
"""
import os
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.main import app  # noqa: E402
from app.services import rag  # noqa: E402

client = TestClient(app)


def _hit(text, source="rti_act_2005_en.pdf", section="Section 7", score=0.82):
    return {
        "text": text,
        "metadata": {
            "source": source, "section": section, "vertical": "rti",
            "act": "The Right to Information Act, 2005", "page_start": 9,
            "section_title": "Disposal of request",
        },
        "score": score,
    }


# --- health -----------------------------------------------------------------

def test_health_reports_structure():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert "status" in body and "knowledge_base_chunks" in body
    assert body["status"] in ("ok", "degraded")


def test_health_reports_configured_models():
    body = client.get("/api/health").json()
    if body["status"] == "ok":
        assert body["embedding_model"] and body["llm_model"]


def test_root_endpoint():
    r = client.get("/")
    assert r.status_code == 200 and "NyayAI" in str(r.json())


# --- request validation -----------------------------------------------------

@pytest.mark.parametrize("payload", [{}, {"question": ""}, {"question": "a"}])
def test_query_rejects_invalid_payloads(payload):
    assert client.post("/api/query", json=payload).status_code == 422


def test_query_rejects_overlong_question():
    assert client.post("/api/query", json={"question": "x" * 3000}).status_code == 422


# --- query path -------------------------------------------------------------

def test_query_returns_full_contract():
    fake = {
        "answer": "Under Section 7, the PIO must reply within thirty days.",
        "vertical": "rti", "language": "en",
        "sources": [{"text": "...", "source": "rti_act_2005_en.pdf",
                     "act": "The Right to Information Act, 2005",
                     "section": "Section 7", "section_title": "Disposal of request",
                     "page": 9, "score": 0.81}],
        "abstained": False,
        "grounding": {"sections_cited": ["7"], "sections_in_context": ["7"],
                      "unsupported_sections": [], "grounded": True},
        "diagnostics": {"top_similarity": 0.81},
        "disclaimer": "This is legal information from official Acts, not legal advice.",
    }
    with patch("app.api.routes_query.rag.answer_question", return_value=fake):
        r = client.post("/api/query", json={"question": "How long does a PIO have to reply?"})
    assert r.status_code == 200
    body = r.json()
    for key in ("answer", "vertical", "language", "sources", "abstained",
                "grounding", "disclaimer"):
        assert key in body
    assert body["sources"][0]["section"] == "Section 7"
    assert body["grounding"]["grounded"] is True


def test_query_returns_503_when_knowledge_base_empty():
    with patch("app.api.routes_query.rag.answer_question",
               side_effect=RuntimeError("Knowledge base is empty")):
        r = client.post("/api/query", json={"question": "How do I file an RTI?"})
    assert r.status_code == 503
    assert "empty" in r.json()["detail"].lower()


def test_query_returns_500_on_unexpected_error():
    with patch("app.api.routes_query.rag.answer_question",
               side_effect=ValueError("boom")):
        r = client.post("/api/query", json={"question": "How do I file an RTI?"})
    assert r.status_code == 500


# --- upload path ------------------------------------------------------------

def test_upload_rejects_unsupported_file_type():
    r = client.post("/api/upload",
                    files={"file": ("test.txt", b"text", "text/plain")})
    assert r.status_code == 400 and "Unsupported file type" in r.json()["detail"]


def test_upload_rejects_missing_file():
    assert client.post("/api/upload").status_code == 422


def test_upload_accepts_image_and_runs_rag():
    with patch("app.services.ocr.extract_text", return_value="Notice about my rent agreement."), \
         patch("app.api.routes_upload.rag.answer_question") as mock_rag:
        mock_rag.return_value = {
            "answer": "Under Section 11 of the Model Tenancy Act, 2021...",
            "vertical": "tenancy", "language": "en", "sources": [],
            "abstained": False, "grounding": {"grounded": True},
            "disclaimer": "info not advice",
        }
        r = client.post("/api/upload",
                        files={"file": ("notice.jpg", b"\xff\xd8\xff\xe0", "image/jpeg")})
    assert r.status_code == 200
    assert "extracted_text" in r.json() and "detected_language" in r.json()


# --- classifier -------------------------------------------------------------

@pytest.mark.parametrize("question,expected", [
    ("How do I file an RTI application?", "rti"),
    ("My landlord is not returning my security deposit.", "tenancy"),
    ("I want a refund for a defective product from an online seller.", "consumer"),
    ("What are the grounds for divorce and maintenance?", "family"),
    ("Police refused to file my FIR — what do I do?", "criminal"),
])
def test_keyword_classifier(question, expected):
    from app.services.classifier import classify_vertical
    assert classify_vertical(question) == expected


# --- language detection -----------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("How do I file an RTI application?", "en"),
    ("", "en"),
    (None, "en"),
])
def test_language_detection(text, expected):
    from app.services.language import detect_language
    assert detect_language(text) == expected


def test_language_detection_devanagari():
    from app.services.language import detect_language
    assert detect_language("सूचना का अधिकार अधिनियम के तहत अपील कैसे करें?") in ("hi", "mr")


# --- grounding / hallucination check ---------------------------------------

def test_grounding_accepts_sections_present_in_context():
    hits = [_hit("Section 7 provides that the Public Information Officer shall reply "
                 "within thirty days of the receipt of the request.")]
    result = rag.check_grounding(
        "The PIO must reply within thirty days (RTI Act, Section 7).", hits)
    assert result["grounded"] is True
    assert result["unsupported_sections"] == []


def test_grounding_flags_invented_section():
    hits = [_hit("Section 7 provides that the officer shall reply within thirty days.")]
    result = rag.check_grounding(
        "You may appeal under Section 42 of the Act.", hits)
    assert result["grounded"] is False
    assert "42" in result["unsupported_sections"]


def test_grounding_counts_metadata_section_as_supported():
    hits = [_hit("The officer shall dispose of the request as expeditiously as possible.",
                 section="Section 7")]
    result = rag.check_grounding("See Section 7 of the Act.", hits)
    assert result["grounded"] is True


def test_grounding_handles_devanagari_citations():
    hits = [_hit("धारा 7 के अनुसार अधिकारी तीस दिनों में उत्तर देगा।", section="Section 7")]
    result = rag.check_grounding("धारा 7 के तहत उत्तर मिलेगा।", hits)
    assert result["grounded"] is True


# --- context construction ---------------------------------------------------

def test_build_context_labels_passages_with_real_citations():
    context = rag.build_context([_hit("Some statutory text about disposal of requests.")])
    assert "[1]" in context
    assert "The Right to Information Act, 2005" in context
    assert "Section 7" in context
    assert "page 9" in context


# --- retrieval strategy -----------------------------------------------------

def test_retrieval_dedupes_repeated_sections():
    from app.services.retrieval import _dedupe_by_section
    hits = [
        _hit("first window of section 7", section="Section 7", score=0.9),
        _hit("second overlapping window of section 7", section="Section 7", score=0.88),
        _hit("text of section 19", section="Section 19", score=0.80),
    ]
    kept = _dedupe_by_section(hits, per_section=1)
    assert len(kept) == 2
    assert [h["metadata"]["section"] for h in kept] == ["Section 7", "Section 19"]


def test_retrieval_allows_two_chunks_from_one_long_section():
    """A long section must be able to contribute more than one chunk."""
    from app.services.retrieval import _dedupe_by_section
    hits = [
        _hit("first window of section 8", section="Section 8", score=0.9),
        _hit("second window of section 8", section="Section 8", score=0.88),
        _hit("third window of section 8", section="Section 8", score=0.86),
    ]
    kept = _dedupe_by_section(hits, per_section=2)
    assert len(kept) == 2


def test_retrieval_abstains_below_threshold():
    from app.core.config import settings
    from app.services import retrieval
    weak = [_hit("unrelated text", score=settings.min_similarity - 0.1)]
    with patch("app.services.retrieval.vectorstore.collection_is_empty", return_value=False), \
         patch("app.services.retrieval.vectorstore.count", return_value=100), \
         patch("app.services.retrieval.embeddings.embed_query", return_value=[0.0] * 8), \
         patch("app.services.retrieval.vectorstore.search", return_value=weak):
        result = retrieval.retrieve("how do I get a US visa?", "general")
    assert result["hits"] == []
    assert result["diagnostics"]["abstained"] is True


def test_retrieval_keeps_hits_above_threshold():
    from app.services import retrieval
    strong = [_hit("relevant statutory text", score=0.78)]
    with patch("app.services.retrieval.vectorstore.collection_is_empty", return_value=False), \
         patch("app.services.retrieval.vectorstore.count", return_value=100), \
         patch("app.services.retrieval.embeddings.embed_query", return_value=[0.0] * 8), \
         patch("app.services.retrieval.vectorstore.search", return_value=strong):
        result = retrieval.retrieve("How long does a PIO have to reply?", "rti")
    assert len(result["hits"]) == 1
    assert result["diagnostics"]["abstained"] is False
    assert result["diagnostics"]["vertical_filter_applied"] == "rti"


def test_retrieval_falls_back_when_filtered_search_is_weak():
    from app.services import retrieval
    weak_filtered = [_hit("marginally related", score=0.40)]
    strong_unfiltered = [_hit("exactly on point", source="bnss_2023.pdf",
                              section="Section 173", score=0.75)]

    def fake_search(vec, n_results=15, vertical_filter=None):
        return weak_filtered if vertical_filter else strong_unfiltered

    with patch("app.services.retrieval.vectorstore.collection_is_empty", return_value=False), \
         patch("app.services.retrieval.vectorstore.count", return_value=100), \
         patch("app.services.retrieval.embeddings.embed_query", return_value=[0.0] * 8), \
         patch("app.services.retrieval.vectorstore.search", side_effect=fake_search):
        result = retrieval.retrieve("police refused my FIR", "rti")
    assert result["diagnostics"]["fallback_to_full_collection"] is True
    assert result["hits"][0]["metadata"]["source"] == "bnss_2023.pdf"


def test_retrieval_raises_when_collection_empty():
    from app.services import retrieval
    with patch("app.services.retrieval.vectorstore.collection_is_empty", return_value=True):
        with pytest.raises(RuntimeError, match="empty"):
            retrieval.retrieve("anything", "rti")


# --- abstention response ----------------------------------------------------

def test_answer_question_abstains_without_calling_llm():
    """An out-of-scope question must not reach the LLM at all."""
    with patch("app.services.rag.classifier.classify_vertical", return_value="general"), \
         patch("app.services.rag.language.detect_language", return_value="en"), \
         patch("app.services.rag.retrieval.retrieve",
               return_value={"hits": [], "diagnostics": {"abstained": True}}), \
         patch("app.services.rag.llm.generate") as mock_llm:
        result = rag.answer_question("How do I get a US tourist visa?")
    mock_llm.assert_not_called()
    assert result["abstained"] is True
    assert result["sources"] == []
    assert "knowledge base" in result["answer"].lower()


# --- document processing ----------------------------------------------------

def test_chunking_cleans_and_labels_sections():
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ingestion"))
    import chunking

    raw = ("7. Disposal of request.-(1) Subject to the proviso to sub-section (2) of "
           "section 5, the Central Public Information Officer shall, as expeditiously as "
           "possible, and in any case within thirty days of the receipt of the request, "
           "either provide the informa-\ntion on payment of such fee as may be prescribed "
           "or reject the request.")
    doc = {"text": chunking.clean_page(raw), "page_spans": [(0, len(raw), 1)]}
    chunks = chunking.chunk_document(doc)
    assert chunks, "expected at least one chunk"
    assert chunks[0]["section"] == "Section 7"
    # Hyphenation across the line break must be repaired.
    assert "information" in chunks[0]["text"]
    assert "informa- tion" not in chunks[0]["text"]


def test_chunking_drops_page_furniture():
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ingestion"))
    import chunking
    cleaned = chunking.clean_page("12\nPage 3 of 46\nActual statutory text follows here.")
    assert "Actual statutory text" in cleaned
    assert "Page 3 of 46" not in cleaned


def test_ungrounded_answer_produces_user_visible_warning():
    """An invented section must not pass silently: the user is warned."""
    hits = [_hit("Section 7 requires a reply within thirty days.")]
    with patch("app.services.rag.classifier.classify_vertical", return_value="rti"), \
         patch("app.services.rag.language.detect_language", return_value="en"), \
         patch("app.services.rag.retrieval.retrieve",
               return_value={"hits": hits, "diagnostics": {"abstained": False}}), \
         patch("app.services.rag.llm.generate",
               return_value="You may appeal under Section 23 within 45 days."):
        result = rag.answer_question("How long does a PIO have?")
    assert result["grounding"]["grounded"] is False
    assert "23" in result["grounding"]["unsupported_sections"]
    assert result["warning"] and "23" in result["warning"]


def test_grounded_answer_has_no_warning():
    hits = [_hit("Section 7 requires a reply within thirty days.")]
    with patch("app.services.rag.classifier.classify_vertical", return_value="rti"), \
         patch("app.services.rag.language.detect_language", return_value="en"), \
         patch("app.services.rag.retrieval.retrieve",
               return_value={"hits": hits, "diagnostics": {"abstained": False}}), \
         patch("app.services.rag.llm.generate",
               return_value="Under Section 7 the PIO must reply within thirty days."):
        result = rag.answer_question("How long does a PIO have?")
    assert result["grounding"]["grounded"] is True
    assert result["warning"] is None


# --- small talk --------------------------------------------------------------

@pytest.mark.parametrize("text", ["Hi", "hello!", "Namaste", "thank you",
                                  "who are you?", "नमस्ते"])
def test_small_talk_gets_greeting_not_refusal(text):
    """A greeting must never reach retrieval or the LLM, and must not be
    answered with the knowledge-base refusal."""
    with patch("app.services.rag.retrieval.retrieve") as mock_ret, \
         patch("app.services.rag.llm.generate") as mock_llm:
        result = rag.answer_question(text)
    mock_ret.assert_not_called()
    mock_llm.assert_not_called()
    assert "NyayAI" in result["answer"]
    assert result["abstained"] is False


def test_real_question_is_not_small_talk():
    assert not rag.is_small_talk("How do I file an RTI application?")
    assert not rag.is_small_talk("hi, my landlord kept my deposit, help me")
