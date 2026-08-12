"""Package the read-only content.sqlite the apps load.

Pulls every verb that has authored practice examples from the service (so the bundle
is meaningful, not empty), and writes the database. The service is the source of
truth; this stage only chooses what to include and where to write.

Choosing is a QA gate, not a filter of convenience: a sentence that failed a check or
that a reviewer refused must never reach a learner, so it is dropped here — and every
drop is reported, because a silent one would read as full coverage.
"""

from __future__ import annotations

from dataclasses import replace

from fil import bundle, example_store, service
from fil.resources import BUILD_DIR
from fil.service import VerbDetail

_OUTPUT = BUILD_DIR / "content.sqlite"


def main() -> None:
    verbs = example_store.stored_verbs()
    if not verbs:
        print("No verbs have examples yet — nothing to package.")
        return

    details = [service.get_verb(root, form) for root, form in verbs]
    shippable = [_without_unshippable_examples(detail) for detail in details]
    _report_dropped(details)

    counts = bundle.write_bundle(shippable, _OUTPUT)

    print(f"Wrote {_OUTPUT.relative_to(BUILD_DIR.parent)}")
    for table, count in counts.items():
        print(f"  {table}: {count}")


def _without_unshippable_examples(detail: VerbDetail) -> VerbDetail:
    kept = tuple(example for example in detail.examples if example.is_shippable)
    return replace(detail, examples=kept)


def _report_dropped(details: list[VerbDetail]) -> None:
    dropped = [
        (detail, example)
        for detail in details
        for example in detail.examples
        if not example.is_shippable
    ]
    if not dropped:
        return

    print(f"Held back {len(dropped)} sentence(s) that did not pass the gate:")
    for detail, example in dropped:
        print(f"  {detail.root} form {detail.form} [{example.tier}]: {example.arabic}")
        print(f"    {_reason(example)}")


def _reason(example) -> str:
    if example.checks is None:
        return "the gate has not run on it"
    if example.checks.gloss_conflicts:
        return f"declared meaning not attested for: {', '.join(example.checks.gloss_conflicts)}"
    if not example.checks.passed:
        return f"failed a check: {example.checks}"
    return f"refused by {example.critique.by}: {example.critique.note or 'no reason given'}"


if __name__ == "__main__":
    main()
