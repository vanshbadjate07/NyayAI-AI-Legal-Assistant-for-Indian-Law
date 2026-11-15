# NyayAI — a multilingual RAG legal assistant for Indian citizens

NyayAI answers everyday legal questions in **English, Hindi and Marathi**,
using only the text of official Indian Acts. Every answer shows the sections
it was built from. When the knowledge base does not cover a question, the
system says so instead of guessing.

Built as a final-year capstone project (RAG track).

> **This is legal information, not legal advice.** It does not replace a
> lawyer, and it will not predict the outcome of a specific case.

---

## What it does

- **Ask in your own language.** A question in Hindi retrieves the relevant
  English statutory text and is answered in Hindi. The embedding model is
  multilingual, so there is no translation step.
- **Answers are grounded.** The model sees only the retrieved Act text and
  is instructed to use nothing else. Each answer is re-read afterwards and
  any section number not present in the retrieved context is flagged.
- **It refuses when it should.** Out-of-scope questions (tax, visas,
  anything not in the knowledge base) are declined with a pointer to free
  legal aid, rather than answered.
- **You can check the work.** Every answer expands to show the five chunks
  used, with Act name, section, page and similarity score. `POST /api/retrieve`
  returns those chunks without generating anything.
- **Photograph a notice.** An image or PDF upload is OCR'd and then answered
  through the same pipeline.

## Legal domains covered

| Domain | Acts indexed |
| --- | --- |
| Right to Information | The Right to Information Act, 2005 (English + Hindi) |
| Tenancy & rent | The Model Tenancy Act, 2021 · The Maharashtra Rent Control Act, 1999 |
| Consumer protection | The Consumer Protection Act, 2019 |
| Family law | The Hindu Marriage Act, 1955 · The Protection of Women from Domestic Violence Act, 2005 |
| Criminal law | The Bharatiya Nyaya Sanhita, 2023 · The Bharatiya Nagarik Suraksha Sanhita, 2023 |

Nine documents in total. Anything outside them is refused by design.

## Stack

Python 3.9+ · FastAPI · ChromaDB · `BAAI/bge-m3` (embeddings) ·
Ollama + `qwen2.5:3b` (generation) · `qwen3-vl:2b-instruct` + EasyOCR (OCR) ·
SQLAlchemy + SQLite · pypdf · langdetect · React 18 + Vite + Tailwind

Everything runs locally. No API keys, no cloud calls, no legal question
leaves the machine.

---

## Running it

### Prerequisites

- Python 3.9 or newer, Node 18 or newer
- [Ollama](https://ollama.com) installed and running
- `poppler` (only needed if you re-run OCR): `brew install poppler`
- ~6 GB free disk (embedding model ~2.2 GB, two Ollama models ~3.8 GB)

### 1. Models

```bash
ollama serve                         # leave running in its own terminal
ollama pull qwen2.5:3b
ollama pull qwen3-vl:2b-instruct
```

### 2. Backend dependencies

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 3. Build the knowledge base

Skip this if `ingestion/chroma_store/` already has content — it ships built.

```bash
# from the repository root, with the venv active
python ingestion/validate_kb.py      # checks all 9 PDFs are readable
python ingestion/ocr_fallback.py     # ~45 min, only for the 2 scanned files
python ingestion/ingest.py           # measured: ~15 min on an M1
```

`validate_kb.py` is worth running first every time: two of the source PDFs in
this project were silently broken (one was an HTML error page saved with a
`.pdf` extension) and produced zero chunks without any error.

### 4. Start the API

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Check it: <http://localhost:8000/api/health> should report
`"status": "ok"` with a non-zero `knowledge_base_chunks`.
Swagger UI is at <http://localhost:8000/docs>.

### 5. Start the frontend

```bash
cd nyayai-frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

---

## Trying it out

Questions that are in scope:

| Domain | Question |
| --- | --- |
| RTI | How do I file an RTI application and how long does the PIO have to reply? |
| Tenancy | My landlord is refusing to return my security deposit. What does the law say? |
| Consumer | I bought a defective product online and the seller refuses a refund. Where do I complain? |
| Family | What is the procedure to claim maintenance after separation? |
| Criminal | The police are refusing to register my FIR. What are my options? |
| Marathi | RTI अर्ज कसा दाखल करायचा आणि किती दिवसांत उत्तर मिळते? |
| Hindi | पुलिस मेरी एफआईआर दर्ज नहीं कर रही है, मुझे क्या करना चाहिए? |

Questions that should be **refused** — worth trying, because refusing well is
a feature here:

- How do I apply for a US tourist visa?
- What is the penalty for late GST filing?
- Write me a Python script that scrapes a website.

To see retrieval on its own, without generation:

```bash
curl -s -X POST http://localhost:8000/api/retrieve \
  -H 'Content-Type: application/json' \
  -d '{"question":"How long does a PIO have to reply to an RTI?"}' | python3 -m json.tool
```

---

## Evaluation

The system is scored against 33 labelled queries (28 in-scope across the five
domains, 5 that must be refused):

```bash
python evaluation/validate_expectations.py   # check the labels against the index
python evaluation/run_eval.py --no-llm       # routing + retrieval only, ~1 min
python evaluation/run_eval.py                # full pipeline, ~20 min
python evaluation/calibrate.py               # abstention threshold sweep
```

Results are written to `evaluation/results/`:

- `eval_report.md` — readable report with per-case results
- `eval_results.json` — full detail, including every retrieved chunk
- `threshold_calibration.json` — the data behind the 0.52 abstention threshold

Measured results (33 cases, final 3,248-chunk index, M1, all models local):

| Metric | Result |
| --- | --- |
| Correct Act among the 5 retrieved chunks (source hit@5) | **100%** |
| Expected section retrieved (section hit@5) | 65.2% |
| Mean precision@5 / MRR | 92.1% / 0.958 |
| Legitimate questions wrongly refused | **0%** |
| Out-of-scope questions correctly refused | 80% (4/5) |
| Answers grounded (no unverifiable section citations) | 85.7% — every violation flagged to the user |
| Answered in the language asked (en/hi/mr) | 100% |
| Mean latency: retrieve / generate | 2.5 s / 21.2 s |

Full detail, including every retrieved chunk and the failure analysis, is in
[`evaluation/results/eval_report.md`](evaluation/results/eval_report.md) and
`PROJECT_REPORT.txt` Section 7.

## Tests

```bash
backend/venv/bin/python -m pytest backend/tests -v
```

35 tests covering request validation, the API contract, the classifier,
language detection, the grounding/hallucination check, the retrieval
strategy (de-duplication, domain fallback, abstention) and document
chunking. No running server required.

---

## Documentation

| File | Contents |
| --- | --- |
| [`docs/architecture.md`](docs/architecture.md) | Architecture, request walkthrough, repo layout |
| [`evaluation/results/eval_report.md`](evaluation/results/eval_report.md) | Generated evaluation report |

## Limitations

- Nine Acts only. Tax, immigration, labour and property-title law are out of
  scope and are refused.
- `qwen2.5:3b` is small. Its summaries can omit a qualifying clause; the
  cited sections are the authoritative part of an answer.
- Two documents are OCR'd (a 60-page scan and a Hindi gazette in a legacy
  font), so their chunks carry OCR noise.
- Login is a front-end mock. There is no real authentication.
- The Docker setup is written but **unverified** — Docker is not installed on
  the development machine. Run it with care.

## Authors

Vansh Badjate and Vaishnavi Nikumbh — Sanjivani University.
Copyright registration SW-2026022947.
