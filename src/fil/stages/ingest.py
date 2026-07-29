"""QAC ingest runner: morphology file -> verb catalogue + a coverage summary.

    python build_qac.py

Reads the corpus, extracts every verb, aggregates by (root, form), writes the
catalogue to build/qac_verbs.json, and prints how the Quran's verbs break down —
the foundation the rest of the engine builds on.
"""

from __future__ import annotations

import json
from collections import Counter

from fil.corpus.catalog import VerbEntry, build_catalog
from fil.corpus.parse import iter_segments, iter_verb_occurrences
from fil.resources import BUILD_DIR, QAC_MORPHOLOGY

_SOURCE = QAC_MORPHOLOGY
_OUTPUT = BUILD_DIR / "qac_verbs.json"


def main() -> None:
    with _SOURCE.open(encoding="utf-8") as lines:
        occurrences = list(iter_verb_occurrences(iter_segments(lines)))
    catalog = build_catalog(occurrences)

    _write_catalog(catalog)
    _print_summary(occurrences, catalog)


def _write_catalog(catalog: list[VerbEntry]) -> None:
    _OUTPUT.parent.mkdir(exist_ok=True)
    records = [
        {"root": e.root, "form": e.form, "lemma": e.lemma,
         "count": e.occurrence_count, "ayat": list(e.ayat)}
        for e in catalog
    ]
    _OUTPUT.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def _print_summary(occurrences, catalog: list[VerbEntry]) -> None:
    distinct_roots = len({e.root for e in catalog})
    by_form = Counter(e.form for e in catalog)

    print(f"Verb occurrences: {len(occurrences)}")
    print(f"Distinct verbs (root+form): {len(catalog)}")
    print(f"Distinct verb roots: {distinct_roots}")
    print("By form:", {f"F{form}": by_form[form] for form in sorted(by_form)})
    print(f"Catalogue -> {_OUTPUT.relative_to(BUILD_DIR.parent)}")
    print("Top verbs:")
    for entry in catalog[:6]:
        print(f"  {entry.lemma:10s} root {entry.root:6s} F{entry.form} — "
              f"{entry.occurrence_count}× in {len(entry.ayat)} ayat")


if __name__ == "__main__":
    main()
