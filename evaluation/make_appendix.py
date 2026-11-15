"""Generates the report appendices from the evaluation results.

The rubric asks for "sample test queries with expected and generated answers"
and "evidence of retrieved document chunks". Rather than transcribe those by
hand into the report — where they would drift out of date and could not be
trusted — they are generated directly from evaluation/results/eval_results.json.

    python evaluation/make_appendix.py > evaluation/results/appendix.txt
"""
import json
import os
import sys
import textwrap

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(THIS_DIR, "results", "eval_results.json")
QUERIES = os.path.join(THIS_DIR, "test_queries.json")

# One representative case per domain, both non-English cases, and two
# refusals — enough to show the system working and declining.
FEATURED = ["rti-01", "ten-01", "con-01", "fam-04", "cri-01",
            "rti-05", "cri-06", "oos-01", "oos-04"]

W = 80


def wrap(text, indent="    ", width=W):
    out = []
    for para in (text or "").split("\n"):
        if not para.strip():
            out.append("")
            continue
        out.extend(textwrap.wrap(para, width=width,
                                 initial_indent=indent, subsequent_indent=indent))
    return "\n".join(out)


def rule(char="-"):
    return char * W


def main() -> int:
    if not os.path.exists(RESULTS):
        print(f"No results at {RESULTS} — run evaluation/run_eval.py first.")
        return 1

    data = json.load(open(RESULTS, encoding="utf-8"))
    cases = {c["id"]: c for c in data["cases"]}
    expected = {c["id"]: c for c in json.load(open(QUERIES, encoding="utf-8"))["cases"]}

    print()
    print("=" * W)
    print("APPENDIX A — SAMPLE TEST QUERIES, EXPECTED AND GENERATED ANSWERS")
    print("=" * W)
    print()
    print(wrap("Generated directly from evaluation/results/eval_results.json so "
               "that what appears here is exactly what the system produced. "
               "Answers are reproduced in full and unedited.", indent=""))
    print()

    for cid in FEATURED:
        case, exp = cases.get(cid), expected.get(cid)
        if not case:
            continue
        print(rule("="))
        print(f"CASE {cid.upper()}   [{case['type']}]   language: {case['language']}")
        print(rule("="))
        print()
        print("QUESTION")
        print(wrap(case["question"]))
        print()

        print("EXPECTED (reference answer from the labelled set)")
        if case["type"] == "in_scope":
            print(wrap(f"Legal domain  : {exp.get('expected_vertical')}"))
            print(wrap(f"Source Act(s) : {', '.join(exp.get('expected_sources', []))}"))
            if exp.get("expected_sections"):
                print(wrap(f"Section(s)    : {', '.join(exp['expected_sections'])}"))
            if exp.get("expected_keywords"):
                print(wrap(f"Must mention  : {', '.join(exp['expected_keywords'])}"))
        else:
            print(wrap("The system must REFUSE this question."))
            print(wrap(f"Reason        : {exp.get('note', '')}"))
        print()

        print("GENERATED ANSWER")
        print(wrap(case.get("answer", "(no answer recorded — run without --no-llm)")))
        print()

        d = case.get("diagnostics", {})
        print("RETRIEVAL")
        print(wrap(f"Classified as         : {case.get('classified_vertical')}"
                   f"  (expected: {case.get('expected_vertical', 'n/a')})"))
        print(wrap(f"Top similarity        : {d.get('top_similarity')}"))
        print(wrap(f"Filter applied        : {d.get('vertical_filter_applied')}"))
        print(wrap(f"Fell back to full KB  : {d.get('fallback_to_full_collection')}"))
        print(wrap(f"Chunks used           : {d.get('chunks_used')}"))
        print(wrap(f"Abstained             : {case.get('abstained')}"))
        if case["type"] == "in_scope" and case.get("retrieval"):
            r = case["retrieval"]
            print(wrap(f"Expected Act retrieved: {r.get('source_hit')}"))
            print(wrap(f"Expected section found: {r.get('section_hit')}"))
            print(wrap(f"Precision@5           : {r.get('precision_at_k')}"))
        print()

        if case.get("generation"):
            g = case["generation"]
            print("VERIFICATION")
            print(wrap(f"Grounded (no invented sections): {g.get('grounded')}"))
            if g.get("unsupported_sections"):
                print(wrap(f"UNSUPPORTED citations         : "
                           f"{', '.join(g['unsupported_sections'])}"))
            found, want = g.get("keywords_found", []), g.get("keywords_expected", [])
            print(wrap(f"Reference keywords found      : {len(found)}/{len(want)}"
                       + (f"  ({', '.join(found)})" if found else "")))
            print(wrap(f"Answered in the right language: {g.get('language_ok')}"))
            print()

        chunks = case.get("retrieved_chunks", [])
        if chunks:
            print("EVIDENCE — RETRIEVED CHUNKS (top 3 of "
                  f"{len(chunks)} passed to the model)")
            print()
            for ch in chunks[:3]:
                print(f"  [{ch['rank']}] score {ch['score']}  |  "
                      f"{ch.get('act') or ch.get('source')}")
                print(f"      {ch.get('section')}"
                      f"{'  page ' + str(ch['page']) if ch.get('page') else ''}"
                      f"  |  file: {ch.get('source')}")
                print(wrap(ch["text_preview"].strip(), indent="      ", width=W))
                print()
        else:
            print("EVIDENCE — no chunks retrieved (question refused).")
            print()

    print()
    print("=" * W)
    print("APPENDIX B — EVIDENCE OF RETRIEVAL, ALL TEST CASES")
    print("=" * W)
    print()
    print(wrap("For every labelled query: what the retrieval stage returned, "
               "before any generation. In-scope cases should retrieve the "
               "expected Act; out-of-scope cases should fall below the "
               "abstention threshold and retrieve nothing.", indent=""))
    print()
    header = f"{'ID':9}{'LANG':6}{'TOP SIM':9}{'ACT RETRIEVED':34}{'SECTIONS RETRIEVED'}"
    print(header)
    print(rule())
    for cid, case in cases.items():
        chunks = case.get("retrieved_chunks", [])
        acts = []
        for ch in chunks:
            src = ch.get("source") or "?"
            if src not in acts:
                acts.append(src)
        secs = []
        for ch in chunks:
            s = (ch.get("section") or "").replace("Section ", "")
            if s and s != "N/A" and s not in secs:
                secs.append(s)
        sim = case.get("diagnostics", {}).get("top_similarity", 0)
        act_str = ", ".join(acts)[:33] if acts else "— refused —"
        print(f"{cid:9}{case['language']:6}{sim:<9}{act_str:34}{', '.join(secs[:8])}")
    print()
    print(wrap("Full text of every retrieved chunk for every case is in "
               "evaluation/results/eval_results.json.", indent=""))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
