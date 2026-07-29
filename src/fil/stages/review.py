"""Export the review queue: every cell where the generator disagrees with the Quran.

This is the small, targeted set a reviewer (or we) look at — not the 25k generated
cells. Thin stage over `fil.service.review_queue()`: it collects the conflicts; this
writes them and shows where they concentrate (by form, by tense).
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict

from fil.resources import BUILD_DIR
from fil.service import Conflict, review_queue

_OUTPUT = BUILD_DIR / "review_queue.json"


def main() -> None:
    conflicts = review_queue()
    _write(conflicts)
    _print_summary(conflicts)


def _write(conflicts: list[Conflict]) -> None:
    _OUTPUT.parent.mkdir(exist_ok=True)
    payload = [asdict(conflict) for conflict in conflicts]
    _OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _print_summary(conflicts: list[Conflict]) -> None:
    print(f"Review queue: {len(conflicts)} conflicts -> {_OUTPUT.relative_to(BUILD_DIR.parent)}")
    by_form = Counter(c.form for c in conflicts)
    print("By form:", {f"F{form}": by_form[form] for form in sorted(by_form)})
    by_tense = Counter(c.tense for c in conflicts)
    print("By tense:", dict(by_tense))
    print("Sample conflicts (Quran vs generator):")
    for c in conflicts[:20]:
        print(f"  {c.root:6s} F{c.form} {c.tense[:4]}/{c.pronoun:7s} "
              f"Quran={c.attested}  gen={c.generated}")


if __name__ == "__main__":
    main()
