"""Checks the reference answers in test_queries.json against the built index.

A labelled set is only useful if the labels are right. For every in-scope
case this confirms that each expected source file is actually indexed and
that each expected section number exists in that file's chunks. Anything it
flags is a mistake in the evaluation set, not a failure of the system, and
must be fixed before the metrics mean anything.

    python evaluation/validate_expectations.py
"""
import json
import os
import re
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(THIS_DIR), "backend"))

from app.services import vectorstore  # noqa: E402

_NUM = re.compile(r"(\d{1,3}[A-Z]?)")


def main() -> int:
    collection = vectorstore.get_collection()
    if collection.count() == 0:
        print("Index is empty — run ingestion/ingest.py first.")
        return 1

    data = collection.get(include=["metadatas"], limit=200000)
    by_source = {}
    for meta in data.get("metadatas") or []:
        if not meta:
            continue
        src = meta.get("source")
        sec = meta.get("section")
        by_source.setdefault(src, set())
        if sec and sec != "N/A":
            for m in _NUM.finditer(str(sec)):
                by_source[src].add(m.group(1))

    print(f"Indexed files: {len(by_source)}")
    for src, secs in sorted(by_source.items()):
        print(f"  {src:34s} {len(secs):4d} distinct section labels")

    cases = json.load(open(os.path.join(THIS_DIR, "test_queries.json"),
                           encoding="utf-8"))["cases"]
    problems = []
    for case in cases:
        if case["type"] != "in_scope":
            continue
        for src in case.get("expected_sources", []):
            if src not in by_source:
                problems.append(f"{case['id']}: expected source '{src}' is not indexed")
        wanted = set(case.get("expected_sections", []))
        if not wanted:
            continue
        available = set()
        for src in case.get("expected_sources", []):
            available |= by_source.get(src, set())
        missing = wanted - available
        if missing == wanted:
            problems.append(
                f"{case['id']}: none of the expected sections {sorted(wanted)} "
                f"exist as labels in {case['expected_sources']}"
            )
        elif missing:
            problems.append(
                f"{case['id']}: expected sections {sorted(missing)} not found "
                f"(found {sorted(wanted & available)}) — acceptable if at least one matches"
            )

    print()
    if not problems:
        print("All reference answers check out against the index.")
        return 0
    print(f"{len(problems)} issue(s) to review:")
    for p in problems:
        print("  -", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
