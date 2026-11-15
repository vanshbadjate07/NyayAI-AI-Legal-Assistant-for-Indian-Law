"""Fills the measured-results slots in PROJECT_REPORT.txt.

Reads:
    ingestion/ingestion_stats.json
    evaluation/results/eval_results.json
    evaluation/results/threshold_calibration.json
    evaluation/results/appendix.txt
Replaces the <<SECTION_7_RESULTS>>, <<SECTION_11>> and <<APPENDIX_AB>>
markers. Idempotent only in the sense that it refuses to run if the markers
are gone, so it cannot double-splice.
"""
import json
import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(THIS_DIR)
REPORT = os.path.join(ROOT, "PROJECT_REPORT.txt")


def pct(v, nd=1):
    return "n/a" if v is None else f"{v * 100:.{nd}f}%"


def main() -> int:
    report = open(REPORT, encoding="utf-8").read()
    for marker in ("<<SECTION_7_RESULTS>>", "<<SECTION_11>>", "<<APPENDIX_AB>>"):
        if marker not in report:
            print(f"Marker {marker} missing — already finalized?")
            return 1

    stats = json.load(open(os.path.join(ROOT, "ingestion", "ingestion_stats.json")))
    ev = json.load(open(os.path.join(THIS_DIR, "results", "eval_results.json")))
    cal = json.load(open(os.path.join(THIS_DIR, "results", "threshold_calibration.json")))
    appendix = open(os.path.join(THIS_DIR, "results", "appendix.txt"),
                    encoding="utf-8").read()

    s = ev["summary"]
    ret, ab = s["retrieval"], s["abstention"]
    gen = s.get("generation", {})
    lat = s.get("latency_s", {})

    ins, outs = cal["in_scope"], cal["out_of_scope"]
    best = cal["recommended_threshold"]
    sep = ("the two distributions are cleanly separable"
           if ins["min"] > outs["max"] else
           "the two distributions overlap, so no threshold is perfect")

    sweep_rows = "\n".join(
        f"     {r['threshold']:<10}{r['in_scope_kept'] * 100:>14.1f}%"
        f"{r['out_of_scope_refused'] * 100:>24.1f}%"
        f"{r['balanced_accuracy'] * 100:>20.1f}%"
        + ("   <- chosen" if abs(r["threshold"] - cal["current_threshold"]) < 1e-9 else "")
        for r in cal["sweep"] if 0.34 < r["threshold"] < 0.61
    )

    sec7 = f"""7.5 MEASURED RESULTS
--------------------------------------------------------------------------------
All numbers in this section are produced by evaluation/run_eval.py and
evaluation/calibrate.py against the final index, and are stored in
evaluation/results/. Hardware: MacBook Air, Apple M1, 8 GB RAM, all models
local.

  Index at evaluation time : {ret.get('collection_chunks', stats['total_chunks'])} chunks
  Cases run                : {s['cases_total']} ({s['cases_in_scope']} in scope, {s['cases_out_of_scope']} out of scope)
  Errors during the run    : {s['errors']}

  (1) ROUTING
     Vertical classification accuracy ............ {pct(s['routing']['vertical_accuracy'])}

  (2) RETRIEVAL (in-scope cases)
     source hit@5  (expected Act retrieved) ...... {pct(ret['source_hit_at_k'])}
     section hit@5 (expected section retrieved) .. {pct(ret['section_hit_at_k'])}
     mean precision@5 ............................ {pct(ret['mean_precision_at_k'])}
     mean reciprocal rank ........................ {ret['mean_mrr']}
     mean top similarity ......................... {ret['mean_top_similarity']}

  (3) ABSTENTION
     correct refusals, out-of-scope .............. {pct(ab['correct_abstention_rate_out_of_scope'])}
     false refusals, in-scope .................... {pct(ab['false_abstention_rate_in_scope'])}
     mean top similarity, in-scope ............... {ab['mean_top_similarity_in_scope']}
     mean top similarity, out-of-scope ........... {ab['mean_top_similarity_out_of_scope']}

     Calibration (evaluation/calibrate.py):
       in-scope     n={ins['n']:<3} min={ins['min']:.4f}  mean={ins['mean']:.4f}  max={ins['max']:.4f}
       out-of-scope n={outs['n']:<3} min={outs['min']:.4f}  mean={outs['mean']:.4f}  max={outs['max']:.4f}
       -> lowest in-scope {ins['min']:.4f} vs highest out-of-scope {outs['max']:.4f}:
          {sep}.

     Threshold sweep (share answered / share refused / balanced accuracy):
     THRESHOLD   IN-SCOPE KEPT   OUT-OF-SCOPE REFUSED   BALANCED ACCURACY
{sweep_rows}
       Best balanced accuracy at {best}; the configured threshold is
       {cal['current_threshold']}.
"""

    if gen:
        sec7 += f"""
  (4) GENERATION ({gen['answers_generated']} answers generated)
     grounded (no invented section numbers) ...... {pct(gen['grounded_rate'])}
     unsupported section citations, total ........ {gen['hallucinated_sections_total']}
     answers citing a section .................... {pct(gen['cites_section_rate'])}
     mean reference-keyword coverage ............. {pct(gen['mean_keyword_coverage'])}
     answered in the language asked .............. {pct(gen['language_correct_rate'])}
     mean answer length .......................... {gen['mean_answer_chars']:.0f} chars

  (5) LATENCY (seconds, mean per stage)
     classify .................................... {lat.get('mean_classify')}
     retrieve (embed + search) ................... {lat.get('mean_retrieve')}
     generate .................................... {lat.get('mean_generate')}
"""

    sec7 += """
  Per-case results, including every retrieved chunk, are in
  evaluation/results/eval_results.json; the readable per-case table is in
  evaluation/results/eval_report.md; representative cases are reproduced in
  Appendix A.

<<INTERPRETATION>>"""

    # ---- Section 11 ----
    files_rows = "\n".join(
        f"     {f['file']:<32}{f['chunks']:>7}   {f.get('text_source', ''):<15}"
        f"{str(f.get('section_labelled_pct', '')) + '%' if f.get('section_labelled_pct') is not None else ''}"
        for f in stats["files"]
    )
    sec11 = f"""

================================================================================
11. RESULTS SUMMARY
================================================================================

11.1 WHAT WAS BUILT
--------------------------------------------------------------------------------
  Knowledge base ........ 9 Acts, 559 pages, 5 legal domains
  Vector index .......... {stats['total_chunks']} chunks, BAAI/bge-m3, ChromaDB (cosine)
  Index build time ...... {stats['build_seconds'] / 60:.0f} minutes on an M1 (one-off)
  Chunking .............. {stats['chunk_size']} chars, {stats['chunk_overlap']} overlap, section-aware

     FILE                              CHUNKS   TEXT SOURCE    SECTION-LABELLED
{files_rows}

11.2 HEADLINE MEASUREMENTS
--------------------------------------------------------------------------------
  Routing accuracy ................... {pct(s['routing']['vertical_accuracy'])}
  Retrieval source hit@5 ............. {pct(ret['source_hit_at_k'])}
  Retrieval section hit@5 ............ {pct(ret['section_hit_at_k'])}
  Out-of-scope correctly refused ..... {pct(ab['correct_abstention_rate_out_of_scope'])}
  In-scope wrongly refused ........... {pct(ab['false_abstention_rate_in_scope'])}"""
    if gen:
        sec11 += f"""
  Grounded answers ................... {pct(gen['grounded_rate'])}
  Answered in the asked language ..... {pct(gen['language_correct_rate'])}
  Mean end-to-end latency ............ ~{(lat.get('mean_classify') or 0) + (lat.get('mean_retrieve') or 0) + (lat.get('mean_generate') or 0):.0f} s per question"""
    sec11 += """

  What these numbers mean, and their limits, are discussed in Sections 7
  and 12. The single most important behaviours for a legal assistant — that
  the right Act is retrieved, that invented citations are caught and flagged,
  and that out-of-scope questions are refused — are all measured above rather
  than assumed.
"""

    report = report.replace("<<SECTION_7_RESULTS>>", sec7)
    report = report.replace("<<SECTION_11>>", sec11)
    report = report.replace("<<APPENDIX_AB>>", appendix.strip("\n"))
    open(REPORT, "w", encoding="utf-8").write(report)
    print("PROJECT_REPORT.txt finalized:",
          len(report.splitlines()), "lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
