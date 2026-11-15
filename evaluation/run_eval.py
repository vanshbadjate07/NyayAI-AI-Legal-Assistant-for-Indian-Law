"""NyayAI RAG evaluation harness.

Scores the pipeline on a labelled query set (evaluation/test_queries.json)
across the three things that can independently go wrong in a RAG system:

  1. ROUTING      — is the question sent to the right Act?
  2. RETRIEVAL    — do the retrieved chunks actually contain the answer?
  3. GENERATION   — is the answer grounded in those chunks, and does it
                    cite them correctly?

Plus the behaviour that matters most for a legal assistant:

  4. ABSTENTION   — is an out-of-scope question refused instead of answered
                    with invented law?

Metrics
-------
source_hit@k      at least one retrieved chunk comes from an expected Act
section_hit@k     at least one retrieved chunk carries an expected section
precision@k       share of the k retrieved chunks from an expected Act
MRR               1/rank of the first chunk from an expected Act
top_similarity    cosine similarity of the best chunk
keyword_coverage  share of the reference keywords present in the answer
grounded          the answer cites no section absent from the context
                  (hallucination check, from rag.check_grounding)
language_ok       the answer is written in the language that was asked
abstained         retrieval scored below the similarity threshold, so no
                  answer was generated

Usage
-----
    python evaluation/run_eval.py                 # full run (LLM + retrieval)
    python evaluation/run_eval.py --no-llm        # retrieval only, fast
    python evaluation/run_eval.py --ids rti-01 con-02
"""
import argparse
import json
import os
import re
import statistics
import sys
import time

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(THIS_DIR)
sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))

from app.core.config import settings  # noqa: E402
from app.services import classifier, llm, rag, retrieval, vectorstore  # noqa: E402

QUERIES_PATH = os.path.join(THIS_DIR, "test_queries.json")
RESULTS_DIR = os.path.join(THIS_DIR, "results")

_SECTION_NUM = re.compile(r"(\d{1,3}[A-Z]?)")


def section_numbers(label) -> set:
    """'Section 13B' -> {'13B'}; tolerates None and 'N/A'."""
    if not label or label == "N/A":
        return set()
    return {m.group(1) for m in _SECTION_NUM.finditer(str(label))}


def devanagari_share(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if "ऀ" <= c <= "ॿ") / len(letters)


def score_retrieval(case: dict, hits: list, top_similarity: float) -> dict:
    expected_sources = set(case.get("expected_sources", []))
    expected_sections = set(case.get("expected_sections", []))

    got_sources = [h["metadata"].get("source") for h in hits]
    got_sections = set()
    for h in hits:
        got_sections |= section_numbers(h["metadata"].get("section"))

    first_rank = next(
        (i + 1 for i, s in enumerate(got_sources) if s in expected_sources), None
    )
    relevant = sum(1 for s in got_sources if s in expected_sources)

    return {
        "retrieved_sources": got_sources,
        "retrieved_sections": sorted(got_sections),
        "source_hit": bool(first_rank),
        "section_hit": bool(expected_sections & got_sections) if expected_sections else None,
        "precision_at_k": round(relevant / len(hits), 3) if hits else 0.0,
        "mrr": round(1 / first_rank, 3) if first_rank else 0.0,
        "first_relevant_rank": first_rank,
        # Taken from diagnostics, not from hits: when the pipeline abstains,
        # hits is deliberately empty but the score that triggered the
        # abstention is exactly what the calibration needs to see.
        "top_similarity": top_similarity,
    }


def score_generation(case: dict, result: dict) -> dict:
    answer = result.get("answer", "") or ""
    keywords = case.get("expected_keywords", []) or []
    present = [k for k in keywords if k.lower() in answer.lower()]

    lang = case.get("language", "en")
    dev = devanagari_share(answer)
    language_ok = dev > 0.35 if lang in ("hi", "mr") else dev < 0.20

    grounding = result.get("grounding") or {}
    return {
        "answer_chars": len(answer),
        "keywords_expected": keywords,
        "keywords_found": present,
        "keyword_coverage": round(len(present) / len(keywords), 3) if keywords else None,
        "cites_section": bool(re.search(r"[Ss]ection\s*\d|धारा|कलम", answer)),
        "grounded": grounding.get("grounded"),
        "unsupported_sections": grounding.get("unsupported_sections", []),
        "language_ok": language_ok,
        "devanagari_share": round(dev, 3),
    }


def run_case(case: dict, use_llm: bool) -> dict:
    record = {"id": case["id"], "question": case["question"],
              "type": case["type"], "language": case.get("language", "en")}

    t0 = time.time()
    vertical = classifier.classify_vertical(case["question"])
    t_classify = time.time() - t0

    t0 = time.time()
    retrieved = retrieval.retrieve(case["question"], vertical)
    t_retrieve = time.time() - t0

    hits = retrieved["hits"]
    record["classified_vertical"] = vertical
    record["expected_vertical"] = case.get("expected_vertical")
    record["vertical_correct"] = (
        vertical == case["expected_vertical"] if case.get("expected_vertical") else None
    )
    record["diagnostics"] = retrieved["diagnostics"]
    record["abstained"] = retrieved["diagnostics"]["abstained"]
    record["timings_s"] = {"classify": round(t_classify, 2),
                           "retrieve": round(t_retrieve, 2)}

    top_similarity = retrieved["diagnostics"].get("top_similarity", 0.0)
    if case["type"] == "in_scope":
        record["retrieval"] = score_retrieval(case, hits, top_similarity)
    else:
        record["retrieval"] = {"top_similarity": top_similarity}
        record["abstention_correct"] = record["abstained"] is True

    # The retrieved chunks are kept in the results file: the rubric asks for
    # evidence of retrieval, and this is that evidence.
    record["retrieved_chunks"] = [
        {
            "rank": i + 1, "score": h["score"],
            "act": h["metadata"].get("act"),
            "section": h["metadata"].get("section"),
            "page": h["metadata"].get("page_start"),
            "source": h["metadata"].get("source"),
            "text_preview": h["text"][:300],
        }
        for i, h in enumerate(hits)
    ]

    if not use_llm:
        return record

    t0 = time.time()
    try:
        result = rag.answer_question(case["question"], case.get("language"))
    except Exception as e:
        record["error"] = f"{type(e).__name__}: {e}"
        return record
    record["timings_s"]["generate"] = round(time.time() - t0, 2)

    record["answer"] = result["answer"]
    record["abstained"] = result.get("abstained", False)
    if case["type"] == "in_scope":
        record["generation"] = score_generation(case, result)
        record["false_abstention"] = record["abstained"]
    else:
        record["abstention_correct"] = record["abstained"] is True
    return record


def summarise(records: list, use_llm: bool) -> dict:
    in_scope = [r for r in records if r["type"] == "in_scope" and "error" not in r]
    out_scope = [r for r in records if r["type"] == "out_of_scope" and "error" not in r]

    def mean(values):
        values = [v for v in values if v is not None]
        return round(statistics.mean(values), 3) if values else None

    answered = [r for r in in_scope if not r.get("abstained")]
    summary = {
        "cases_total": len(records),
        "cases_in_scope": len(in_scope),
        "cases_out_of_scope": len(out_scope),
        "errors": sum(1 for r in records if "error" in r),
        "routing": {
            "vertical_accuracy": mean([1.0 if r["vertical_correct"] else 0.0
                                       for r in in_scope if r["vertical_correct"] is not None]),
        },
        "retrieval": {
            "source_hit_at_k": mean([1.0 if r["retrieval"]["source_hit"] else 0.0 for r in in_scope]),
            "section_hit_at_k": mean([1.0 if r["retrieval"]["section_hit"] else 0.0
                                      for r in in_scope if r["retrieval"].get("section_hit") is not None]),
            "mean_precision_at_k": mean([r["retrieval"]["precision_at_k"] for r in in_scope]),
            "mean_mrr": mean([r["retrieval"]["mrr"] for r in in_scope]),
            "mean_top_similarity": mean([r["retrieval"]["top_similarity"] for r in in_scope]),
            "top_k": settings.top_k,
            "fetch_k": settings.fetch_k,
        },
        "abstention": {
            "false_abstention_rate_in_scope": mean([1.0 if r.get("abstained") else 0.0 for r in in_scope]),
            "correct_abstention_rate_out_of_scope": mean(
                [1.0 if r.get("abstention_correct") else 0.0 for r in out_scope]
            ),
            "mean_top_similarity_in_scope": mean([r["retrieval"]["top_similarity"] for r in in_scope]),
            "mean_top_similarity_out_of_scope": mean([r["retrieval"]["top_similarity"] for r in out_scope]),
            "threshold": settings.min_similarity,
        },
    }

    if use_llm:
        summary["generation"] = {
            "answers_generated": len(answered),
            "grounded_rate": mean([1.0 if r["generation"]["grounded"] else 0.0 for r in answered]),
            "hallucinated_sections_total": sum(
                len(r["generation"]["unsupported_sections"]) for r in answered
            ),
            "cites_section_rate": mean([1.0 if r["generation"]["cites_section"] else 0.0 for r in answered]),
            "mean_keyword_coverage": mean([r["generation"]["keyword_coverage"] for r in answered]),
            "language_correct_rate": mean([1.0 if r["generation"]["language_ok"] else 0.0 for r in answered]),
            "mean_answer_chars": mean([float(r["generation"]["answer_chars"]) for r in answered]),
        }
        gen_times = [r["timings_s"].get("generate") for r in records if r["timings_s"].get("generate")]
        summary["latency_s"] = {
            "mean_retrieve": mean([r["timings_s"]["retrieve"] for r in records]),
            "mean_classify": mean([r["timings_s"]["classify"] for r in records]),
            "mean_generate": mean(gen_times),
        }
    return summary


def write_report(summary: dict, records: list, path: str, use_llm: bool) -> None:
    def pct(v):
        return "n/a" if v is None else f"{v * 100:.1f}%"

    lines = [
        "# NyayAI — RAG Evaluation Report",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Mode: {'full pipeline (retrieval + generation)' if use_llm else 'retrieval only'}",
        "",
        "## Configuration",
        "",
        "| Setting | Value |",
        "| --- | --- |",
        f"| Embedding model | `{settings.embed_model}` |",
        f"| LLM | `{settings.llm_model}` |",
        f"| Chunks in index | {vectorstore.count()} |",
        f"| Candidates fetched (fetch_k) | {settings.fetch_k} |",
        f"| Chunks passed to LLM (top_k) | {settings.top_k} |",
        f"| Abstention threshold | {settings.min_similarity} cosine |",
        f"| Filter-fallback threshold | {settings.fallback_similarity} cosine |",
        "",
        "## Results",
        "",
        f"Cases: {summary['cases_total']} "
        f"({summary['cases_in_scope']} in scope, {summary['cases_out_of_scope']} out of scope). "
        f"Errors: {summary['errors']}.",
        "",
        "### 1. Routing (question -> legal domain)",
        "",
        f"- Vertical classification accuracy: **{pct(summary['routing']['vertical_accuracy'])}**",
        "",
        "### 2. Retrieval",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Source hit@{settings.top_k} (expected Act retrieved) | **{pct(summary['retrieval']['source_hit_at_k'])}** |",
        f"| Section hit@{settings.top_k} (expected section retrieved) | **{pct(summary['retrieval']['section_hit_at_k'])}** |",
        f"| Mean precision@{settings.top_k} | {pct(summary['retrieval']['mean_precision_at_k'])} |",
        f"| Mean reciprocal rank | {summary['retrieval']['mean_mrr']} |",
        f"| Mean top similarity | {summary['retrieval']['mean_top_similarity']} |",
        "",
        "### 3. Abstention / hallucination guard",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Correct refusals on out-of-scope questions | **{pct(summary['abstention']['correct_abstention_rate_out_of_scope'])}** |",
        f"| False refusals on in-scope questions | {pct(summary['abstention']['false_abstention_rate_in_scope'])} |",
        f"| Mean top similarity, in scope | {summary['abstention']['mean_top_similarity_in_scope']} |",
        f"| Mean top similarity, out of scope | {summary['abstention']['mean_top_similarity_out_of_scope']} |",
        "",
    ]

    if use_llm and "generation" in summary:
        g = summary["generation"]
        lines += [
            "### 4. Generation",
            "",
            "| Metric | Value |",
            "| --- | --- |",
            f"| Answers generated | {g['answers_generated']} |",
            f"| Grounded (no invented section numbers) | **{pct(g['grounded_rate'])}** |",
            f"| Unsupported section citations, total | **{g['hallucinated_sections_total']}** |",
            f"| Answers citing a section | {pct(g['cites_section_rate'])} |",
            f"| Mean reference-keyword coverage | {pct(g['mean_keyword_coverage'])} |",
            f"| Answered in the language asked | {pct(g['language_correct_rate'])} |",
            f"| Mean answer length | {g['mean_answer_chars']:.0f} chars |",
            "",
            "### Latency (seconds, M1 CPU, local models)",
            "",
            "| Stage | Mean |",
            "| --- | --- |",
            f"| Classify | {summary['latency_s']['mean_classify']} |",
            f"| Retrieve (embed + search) | {summary['latency_s']['mean_retrieve']} |",
            f"| Generate | {summary['latency_s']['mean_generate']} |",
            "",
        ]

    lines += ["## Per-case results", "",
              "| ID | Lang | Vertical | Src hit | Sec hit | Top sim | " +
              ("Grounded | Keywords | " if use_llm else "") + "Notes |",
              "| --- | --- | --- | --- | --- | --- | " + ("--- | --- | " if use_llm else "") + "--- |"]

    for r in records:
        if r["type"] == "out_of_scope":
            ok = "refused" if r.get("abstained") else "ANSWERED (should refuse)"
            row = (f"| {r['id']} | {r['language']} | out-of-scope | - | - | "
                   f"{r['retrieval']['top_similarity']} | ")
            if use_llm:
                row += "- | - | "
            lines.append(row + f"{ok} |")
            continue

        ret = r["retrieval"]
        vert = ("ok" if r.get("vertical_correct") else
                f"{r['classified_vertical']}≠{r['expected_vertical']}")
        row = (f"| {r['id']} | {r['language']} | {vert} | "
               f"{'yes' if ret.get('source_hit') else 'NO'} | "
               f"{'yes' if ret.get('section_hit') else ('NO' if ret.get('section_hit') is not None else '-')} | "
               f"{ret.get('top_similarity')} | ")
        note = ""
        if use_llm and "generation" in r:
            g = r["generation"]
            row += f"{'yes' if g['grounded'] else 'NO'} | "
            cov = g["keyword_coverage"]
            row += (f"{len(g['keywords_found'])}/{len(g['keywords_expected'])}"
                    if g["keywords_expected"] else "-") + " | "
            if g["unsupported_sections"]:
                note = "invented sections: " + ", ".join(g["unsupported_sections"])
            elif cov is not None and cov < 1.0:
                note = "missing: " + ", ".join(
                    k for k in g["keywords_expected"] if k not in g["keywords_found"])
        if r.get("abstained"):
            note = ("refused an in-scope question; " + note).strip("; ")
        if "error" in r:
            note = r["error"]
        lines.append(row + f"{note or 'ok'} |")

    lines += ["", "Full per-case detail, including every retrieved chunk, is in "
              "`evaluation/results/eval_results.json`.", ""]

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-llm", action="store_true",
                    help="score routing and retrieval only (no generation)")
    ap.add_argument("--ids", nargs="*", help="run only these case ids")
    ap.add_argument("--out", default=RESULTS_DIR)
    args = ap.parse_args()
    use_llm = not args.no_llm

    os.makedirs(args.out, exist_ok=True)
    cases = json.load(open(QUERIES_PATH, encoding="utf-8"))["cases"]
    if args.ids:
        cases = [c for c in cases if c["id"] in args.ids]

    if vectorstore.collection_is_empty():
        print("Knowledge base is empty — run 'python ingestion/ingest.py' first.")
        return 1
    print(f"Index: {vectorstore.count()} chunks | embed={settings.embed_model} "
          f"| llm={settings.llm_model} | top_k={settings.top_k} "
          f"| threshold={settings.min_similarity}")
    if use_llm:
        try:
            llm.generate("Reply with the single word: ready")
        except Exception as e:
            print(f"LLM unreachable ({e}). Re-run with --no-llm, or start 'ollama serve'.")
            return 1

    records = []
    started = time.time()
    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] {case['id']}: {case['question'][:66]}...", flush=True)
        try:
            records.append(run_case(case, use_llm))
        except Exception as e:
            records.append({"id": case["id"], "question": case["question"],
                            "type": case["type"], "language": case.get("language", "en"),
                            "error": f"{type(e).__name__}: {e}",
                            "timings_s": {}, "retrieval": {"top_similarity": 0.0}})
            print(f"    error: {e}")

    summary = summarise(records, use_llm)
    summary["elapsed_s"] = round(time.time() - started, 1)

    json_path = os.path.join(args.out, "eval_results.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump({"summary": summary, "cases": records}, fh, indent=2, ensure_ascii=False)
    md_path = os.path.join(args.out, "eval_report.md")
    write_report(summary, records, md_path, use_llm)

    print("\n" + json.dumps(summary, indent=2))
    print(f"\nWrote {json_path}\nWrote {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
