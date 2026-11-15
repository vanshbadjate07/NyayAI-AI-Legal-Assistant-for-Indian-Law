import os

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ — the directory that holds app/. Relative paths in .env are
# resolved against this, not against the current working directory, so the
# server and the scripts behave the same no matter where they are started
# from. Before this, `uvicorn app.main:app` only worked from inside
# backend/ and failed with an opaque "unable to open database file".
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _resolve(path: str) -> str:
    return path if os.path.isabs(path) else os.path.normpath(os.path.join(BACKEND_ROOT, path))


class Settings(BaseSettings):
    # --- models ---
    ollama_host: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:3b"
    # Vision model for OCR of uploaded images. qwen3-vl:2b-instruct replaced
    # moondream: it reads Devanagari as well as Latin script, where moondream
    # is English-only, and it is already a 2B model so it still fits in 8GB.
    vision_model: str = "qwen3-vl:2b-instruct"
    embed_model: str = "BAAI/bge-m3"

    # --- vector store ---
    chroma_dir: str = "../ingestion/chroma_store"
    chroma_collection: str = "nyayai_legal_kb"
    data_dir: str = "../data/legal_docs"
    db_url: str = "sqlite:///./app/db/nyayai.db"

    # --- retrieval ---
    # Candidates pulled from Chroma before de-duplication.
    fetch_k: int = 15
    # Chunks finally passed to the LLM as context.
    top_k: int = 5
    # Most chunks kept from any one section. 1 was too strict: a long section
    # (the RTI exemptions, for instance) legitimately needs two consecutive
    # chunks to be understood. 2 still stops five overlapping windows of one
    # provision from crowding out every other section.
    max_chunks_per_section: int = 2
    # Below this cosine similarity the system abstains instead of answering.
    # Calibrated against the labelled query set (evaluation/calibrate.py):
    # at 0.52 every in-scope query is still answered and 4 of 5 out-of-scope
    # queries are refused. The sweep's best balanced accuracy (0.575) was
    # rejected because it wrongly refuses 18% of legitimate questions.
    min_similarity: float = 0.52
    # Below this, the vertical filter is dropped and the whole collection is
    # searched (guards against a misclassified question).
    fallback_similarity: float = 0.55

    # --- generation ---
    llm_temperature: float = 0.2
    llm_num_ctx: int = 8192
    # Hard cap on generated tokens. Without it, qwen2.5:3b occasionally
    # rambles open-endedly in Devanagari — one Marathi answer ran for 24
    # minutes before this cap existed. 800 tokens is ~3x a typical complete
    # answer.
    llm_num_predict: int = 800

    model_config = SettingsConfigDict(
        env_file=os.path.join(BACKEND_ROOT, ".env"), extra="ignore"
    )

    def model_post_init(self, __context) -> None:
        # Make filesystem settings absolute and make sure the SQLite
        # directory exists, so a fresh clone runs without manual setup.
        object.__setattr__(self, "chroma_dir", _resolve(self.chroma_dir))
        object.__setattr__(self, "data_dir", _resolve(self.data_dir))

        if self.db_url.startswith("sqlite:///") and not self.db_url.startswith("sqlite:////"):
            rel = self.db_url[len("sqlite:///"):]
            abs_path = _resolve(rel)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            object.__setattr__(self, "db_url", f"sqlite:///{abs_path}")


settings = Settings()
