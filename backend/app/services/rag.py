"""The RAG pipeline: classify -> retrieve -> generate -> verify.

Design notes that matter for a legal assistant:

* **Grounding is enforced twice.** The prompt restricts the model to the
  retrieved context, and `check_grounding()` then re-reads the generated
  answer and flags any section number that does not appear in the context
  that was actually supplied. A legal answer citing an invented section is
  the one failure mode that could cause real harm, so it is measured
  rather than assumed.

* **Abstention is a valid answer.** If retrieval scores below the
  similarity threshold, no LLM call is made at all and the user is told
  the knowledge base does not cover the question. This is what keeps an
  out-of-scope question ("how do I get a US visa?") from being answered
  with confident nonsense.

* **Cross-lingual retrieval.** bge-m3 is a multilingual embedding model,
  so a Hindi or Marathi question retrieves the relevant English statutory
  text directly, and the LLM is instructed to answer in the user's
  language while citing the English Act. No translation step is needed.
"""
import re
from typing import Dict, List, Optional

from app.core.config import settings
from app.services import classifier, embeddings, language, llm, retrieval
from app.services.language import LANG_NAMES_FOR_PROMPT

SYSTEM_PROMPT = """You are NyayAI, a legal information assistant for Indian citizens.

Rules you must follow:
1. Answer ONLY from the numbered context passages provided. They are extracts from official Indian Acts.
2. Cite the Act name and section number for every legal statement you make, e.g. "(The Right to Information Act, 2005, Section 7)".
3. Never state a section number, case name, time limit, fee or penalty that does not appear in the context.
4. If the context does not answer the question, say exactly what is missing and advise consulting a lawyer or a local legal aid clinic. Do not fill the gap with general knowledge.
5. Be practical: state the person's right, then the steps to take, in plain language a non-lawyer can act on.
6. Do not give a verdict on the person's specific case or promise an outcome. This is legal information, not legal advice.
7. Write the entire answer in {lang_name}.
"""

NO_CONTEXT_MESSAGE = {
    "en": ("I could not find anything in my knowledge base that covers this question. "
           "My knowledge base contains Indian law on Right to Information, tenancy, "
           "consumer protection, family law and criminal procedure. For anything else, "
           "or for advice on your specific case, please consult a lawyer or your "
           "nearest District Legal Services Authority (free legal aid)."),
    "hi": ("मुझे अपने ज्ञान-भंडार में इस प्रश्न से संबंधित कोई प्रावधान नहीं मिला। "
           "मेरे पास सूचना का अधिकार, किरायेदारी, उपभोक्ता संरक्षण, पारिवारिक कानून और "
           "आपराधिक प्रक्रिया से जुड़े भारतीय कानून हैं। अन्य विषयों के लिए कृपया वकील या "
           "अपने जिला विधिक सेवा प्राधिकरण (निःशुल्क विधिक सहायता) से संपर्क करें।"),
    "mr": ("माझ्या ज्ञानसंग्रहात या प्रश्नाशी संबंधित कोणतीही तरतूद मला सापडली नाही. "
           "माझ्याकडे माहितीचा अधिकार, भाडेकरू, ग्राहक संरक्षण, कौटुंबिक कायदा आणि "
           "फौजदारी प्रक्रिया यासंबंधीचे भारतीय कायदे आहेत. इतर विषयांसाठी कृपया वकील "
           "किंवा आपल्या जिल्हा विधी सेवा प्राधिकरणाशी (मोफत कायदेशीर मदत) संपर्क साधा."),
}

# Shown to the user when the grounding check finds a citation that is not in
# the retrieved context. The answer is still returned — it may be useful —
# but the user is told not to trust the citation, which is the specific part
# that is unsafe.
UNGROUNDED_WARNING = {
    "en": ("Caution: this answer cites section {sections}, which does not appear in "
           "the retrieved text of the Act. Treat that citation as unverified and "
           "check it against the sources below before relying on it."),
    "hi": ("सावधानी: इस उत्तर में धारा {sections} का उल्लेख है, जो अधिनियम के प्राप्त "
           "अंश में नहीं मिली। इस संदर्भ को असत्यापित मानें और नीचे दिए स्रोतों से जाँच लें।"),
    "mr": ("सावधान: या उत्तरात कलम {sections} चा उल्लेख आहे, जे मिळालेल्या कायद्याच्या "
           "मजकुरात आढळले नाही. हा संदर्भ अपुष्ट समजा आणि खालील स्रोतांशी तपासा."),
}

DISCLAIMER = {
    "en": "This is legal information from official Acts, not legal advice.",
    "hi": "यह आधिकारिक अधिनियमों से ली गई कानूनी जानकारी है, कानूनी सलाह नहीं।",
    "mr": "ही अधिकृत कायद्यांमधील कायदेशीर माहिती आहे, कायदेशीर सल्ला नाही.",
}

_SECTION_IN_TEXT = re.compile(r"[Ss]ection\s+(\d{1,3}[A-Z]?)|(?:धारा|कलम)\s*(\d{1,3})")

# Greetings and small talk are not legal questions; without this they fall
# through retrieval, score below the abstention threshold, and the user's
# "Hi" is answered with "I could not find anything in my knowledge base" —
# correct behaviour, terrible manners.
_SMALL_TALK = re.compile(
    r"^\s*(hi+|hii+|hello+|hey+|yo|namaste|namaskar|नमस्ते|नमस्कार|"
    r"good\s*(morning|afternoon|evening)|how are you\??|"
    r"thanks?|thank you|धन्यवाद|शुक्रिया|ok(ay)?|"
    r"who are you\??|what (are|can) you( do)?\??|help)\s*[.!?]*\s*$",
    re.IGNORECASE,
)

GREETING_MESSAGE = {
    "en": ("Namaste! I am NyayAI. Ask me a legal question in English, Hindi or "
           "Marathi and I will answer from official Indian Acts, citing the "
           "exact sections. I cover the Right to Information, tenancy and "
           "rent, consumer protection, family law, and criminal law. For "
           "example: \"My landlord is not returning my security deposit — "
           "what does the law say?\""),
    "hi": ("नमस्ते! मैं NyayAI हूँ। मुझसे अंग्रेज़ी, हिंदी या मराठी में कानूनी प्रश्न पूछिए — "
           "मैं आधिकारिक भारतीय अधिनियमों से, धाराओं के संदर्भ सहित उत्तर दूँगा। "
           "मेरे विषय: सूचना का अधिकार, किरायेदारी, उपभोक्ता संरक्षण, पारिवारिक कानून "
           "और आपराधिक कानून।"),
    "mr": ("नमस्कार! मी NyayAI आहे। मला इंग्रजी, हिंदी किंवा मराठीत कायदेशीर प्रश्न विचारा — "
           "मी अधिकृत भारतीय कायद्यांमधून, कलमांच्या संदर्भासह उत्तर देईन। "
           "माझे विषय: माहितीचा अधिकार, भाडेकरू, ग्राहक संरक्षण, कौटुंबिक कायदा "
           "आणि फौजदारी कायदा।"),
}


def is_small_talk(question: str) -> bool:
    return bool(_SMALL_TALK.match((question or "").strip()))


def build_context(hits: List[Dict]) -> str:
    """Numbers each passage and labels it with its real citation, so the
    model can cite the Act rather than a filename."""
    blocks = []
    for i, hit in enumerate(hits, start=1):
        m = hit["metadata"]
        label = f"{m.get('act', m.get('source', 'unknown'))}"
        section = m.get("section") or "N/A"
        pages = m.get("page_start")
        head = f"[{i}] {label} — {section}"
        if m.get("section_title"):
            head += f" ({m['section_title']})"
        if pages:
            head += f", page {pages}"
        blocks.append(f"{head}\n{hit['text']}")
    return "\n\n".join(blocks)


def check_grounding(answer: str, hits: List[Dict]) -> Dict:
    """Flags section numbers cited in the answer that do not appear in the
    retrieved context — a direct, automatable hallucination check."""
    context = " ".join(h["text"] for h in hits)
    context_sections = {
        (m.group(1) or m.group(2)) for m in _SECTION_IN_TEXT.finditer(context)
    }
    # Section labels attached as metadata count as supported too.
    for hit in hits:
        sec = str(hit["metadata"].get("section", ""))
        found = re.search(r"(\d{1,3}[A-Z]?)", sec)
        if found:
            context_sections.add(found.group(1))

    answer_sections = {
        (m.group(1) or m.group(2)) for m in _SECTION_IN_TEXT.finditer(answer)
    }
    unsupported = sorted(answer_sections - context_sections)
    return {
        "sections_cited": sorted(answer_sections),
        "sections_in_context": sorted(context_sections),
        "unsupported_sections": unsupported,
        "grounded": not unsupported,
    }


def answer_question(
    question: str,
    language_override: Optional[str] = None,
    include_diagnostics: bool = True,
) -> dict:
    lang = language_override or language.detect_language(question)
    lang_name = LANG_NAMES_FOR_PROMPT.get(lang, "English")

    if is_small_talk(question):
        return {
            "answer": GREETING_MESSAGE.get(lang, GREETING_MESSAGE["en"]),
            "vertical": "general",
            "language": lang,
            "sources": [],
            "abstained": False,
            "grounding": {"sections_cited": [], "sections_in_context": [],
                          "unsupported_sections": [], "grounded": True},
            "warning": None,
            "diagnostics": {"small_talk": True} if include_diagnostics else None,
            "disclaimer": None,
        }

    vertical = classifier.classify_vertical(question)

    result = retrieval.retrieve(question, vertical)
    hits = result["hits"]
    diagnostics = result["diagnostics"]

    if not hits:
        return {
            "answer": NO_CONTEXT_MESSAGE.get(lang, NO_CONTEXT_MESSAGE["en"]),
            "vertical": vertical,
            "language": lang,
            "sources": [],
            "abstained": True,
            "grounding": {"sections_cited": [], "sections_in_context": [],
                          "unsupported_sections": [], "grounded": True},
            "warning": None,
            "diagnostics": diagnostics if include_diagnostics else None,
            "disclaimer": DISCLAIMER.get(lang, DISCLAIMER["en"]),
        }

    context = build_context(hits)
    system = SYSTEM_PROMPT.format(lang_name=lang_name)
    prompt = (
        f"Context passages:\n{context}\n\n"
        f"Question: {question}\n\n"
        f"Answer in {lang_name}, citing the Act and section for each point:"
    )

    answer_text = llm.generate(prompt, system=system)
    grounding = check_grounding(answer_text, hits)

    # The check is only worth running if it changes what the user sees.
    warning = None
    if not grounding["grounded"]:
        template = UNGROUNDED_WARNING.get(lang, UNGROUNDED_WARNING["en"])
        warning = template.format(sections=", ".join(grounding["unsupported_sections"]))

    sources = [
        {
            "text": h["text"][:400],
            "source": h["metadata"].get("source", "unknown"),
            "act": h["metadata"].get("act"),
            "section": h["metadata"].get("section"),
            "section_title": h["metadata"].get("section_title") or None,
            "page": h["metadata"].get("page_start") or None,
            "score": h["score"],
        }
        for h in hits
    ]

    return {
        "answer": answer_text,
        "vertical": vertical,
        "language": lang,
        "sources": sources,
        "abstained": False,
        "grounding": grounding,
        "warning": warning,
        "diagnostics": diagnostics if include_diagnostics else None,
        "disclaimer": DISCLAIMER.get(lang, DISCLAIMER["en"]),
    }
