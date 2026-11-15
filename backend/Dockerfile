# NyayAI backend — FastAPI + ChromaDB client.
#
# Scope: this image contains the API only. Two things stay outside it:
#
#   1. Ollama (qwen2.5:3b, qwen3-vl:2b-instruct) runs as its own service —
#      see docker-compose.yml — and is reached over OLLAMA_HOST.
#   2. The Chroma vector store is built on the host by
#      `python ingestion/ingest.py` and mounted read-only at /app/chroma_store.
#      It is a build artefact of the source PDFs, not source code, so it is
#      not copied into the image. (An earlier version of this file tried
#      `COPY ../ingestion/chroma_store/`, which can never work: the build
#      context is ./backend, and Docker cannot read above its context.)
#
# Build from the repository root:
#   docker compose build
# Or directly:
#   docker build -t nyayai-backend ./backend

FROM python:3.11-slim

# libgl1/libglib2.0-0 are needed by opencv-python-headless, which EasyOCR
# pulls in for the upload-OCR path.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first, so code changes do not invalidate the pip layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY .env.example ./.env.example

# SQLite query log lives here; mounted as a named volume in compose so it
# survives container replacement.
RUN mkdir -p /app/app/db

EXPOSE 8000

# Reports degraded (not unhealthy) if Ollama is down but the API is up, so
# this only fails when the process itself is not serving.
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/health').status==200 else 1)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
