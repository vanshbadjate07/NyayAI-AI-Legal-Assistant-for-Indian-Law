"""Calibrates the abstention threshold from data instead of guessing it.

`settings.min_similarity` decides when NyayAI refuses to answer. Set it too
low and out-of-scope questions get confident invented answers; too high and
real questions are refused. This script embeds every labelled query, records
the top cosine similarity, and reports the separation between the in-scope
and out-of-scope distributions, then sweeps candidate thresholds and prints
the accuracy of each so the chosen value can be justified.

    python evaluation/calibrate.py
"""
import json
import os
import statistics
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(THIS_DIR), "backend"))

from app.core.config import settings  # noqa: E402
from app.services import classifier, embeddings, vectorstore  # noqa: E402

OUT_PATH = os.path.join(THIS_DIR, "results", "threshold_calibration.json")


def top_similarity(question: str) -> float:
    vertical = classifier.classify_vertical(question)
    vec = embeddings.embed_query(question)
    filt = vertical if vertical != "general" else None
    hits = vectorstore.search(vec, n_results=settings.fetch_k, vertical_filter=filt)
    best = hits[0]["score"] if hits else 0.0
    if filt and best < settings.fallback_similarity:
        hits = vectorstore.search(vec, n_results=settings.fetch_k, vertical_filter=None)
        best = max(best, hits[0]["score"] if hits else 0.0)
    return best


def main() -> int:
    if vectorstore.collection_is_empty():
        print("Index is empty — run ingestion/ingest.py first.")
        return 1

    cases = json.load(open(os.path.join(THIS_DIR, "test_queries.json"),
                           encoding="utf-8"))["cases"]
    scored = []
    for case in cases:
        score = top_similarity(case["question"])
        scored.append({"id": case["id"], "type": case["type"], "top_similarity": score})
        print(f"{case['id']:8s} {case['type']:13s} {score:.4f}  {case['question'][:52]}")

    ins = [s["top_similarity"] for s in scored if s["type"] == "in_scope"]
    outs = [s["top_similarity"] for s in scored if s["type"] == "out_of_scope"]

    print("\nin-scope      n=%d  min=%.4f  mean=%.4f  max=%.4f"
          % (len(ins), min(ins), statistics.mean(ins), max(ins)))
    print("out-of-scope  n=%d  min=%.4f  mean=%.4f  max=%.4f"
          % (len(outs), min(outs), statistics.mean(outs), max(outs)))
    print("\nseparation: lowest in-scope = %.4f, highest out-of-scope = %.4f  -> %s"
          % (min(ins), max(outs),
             "cleanly separable" if min(ins) > max(outs) else "overlapping"))

    print("\nthreshold  in-scope kept  out-of-scope refused  balanced accuracy")
    sweep = []
    for t in [round(0.25 + 0.025 * i, 3) for i in range(21)]:
        kept = sum(1 for v in ins if v >= t) / len(ins)
        refused = sum(1 for v in outs if v < t) / len(outs)
        balanced = (kept + refused) / 2
        sweep.append({"threshold": t, "in_scope_kept": round(kept, 3),
                      "out_of_scope_refused": round(refused, 3),
                      "balanced_accuracy": round(balanced, 3)})
        marker = "   <- current" if abs(t - settings.min_similarity) < 1e-9 else ""
        print(f"  {t:<9} {kept * 100:12.1f}% {refused * 100:20.1f}% "
              f"{balanced * 100:17.1f}%{marker}")

    best = max(sweep, key=lambda r: (r["balanced_accuracy"], r["threshold"]))
    print(f"\nBest balanced accuracy at threshold {best['threshold']} "
          f"({best['balanced_accuracy'] * 100:.1f}%). Current setting: "
          f"{settings.min_similarity}.")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as fh:
        json.dump({"per_query": scored, "sweep": sweep,
                   "current_threshold": settings.min_similarity,
                   "recommended_threshold": best["threshold"],
                   "in_scope": {"n": len(ins), "min": min(ins),
                                "mean": statistics.mean(ins), "max": max(ins)},
                   "out_of_scope": {"n": len(outs), "min": min(outs),
                                    "mean": statistics.mean(outs), "max": max(outs)}},
                  fh, indent=2)
    print(f"Wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
