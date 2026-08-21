"""Plan what the factory owes, and report where every sentence job stands.

Frequency first: the most-used verbs are planned before the rare ones, because ~300 verbs
carry most of the Quran and doing those well beats doing all 1473 badly. Planning is
idempotent, so running this again after adding verbs only adds what is genuinely new.
"""

from __future__ import annotations

from fil import service

# How far down the frequency list one run plans. Bounded on purpose: a batch we can
# actually finish keeps the agenda honest, and re-running simply extends it.
_VERBS_PER_RUN = 25


def main() -> None:
    _plan(_VERBS_PER_RUN)
    service.sync_agenda()  # sentences that already exist are not work still owing
    _report()


def _plan(verb_count: int) -> None:
    planned = 0
    for summary in service.list_verbs(limit=verb_count):
        planned += len(service.plan_verb(summary.root, summary.form))
    print(f"Planned {planned} new sentence job(s) across the top {verb_count} verbs.")


def _report() -> None:
    status = service.agenda_status()
    total = sum(status.values())
    print(f"\nAgenda — {total} job(s):")
    for state, count in status.items():
        print(f"  {state:<9} {count}")

    job = service.next_job()
    if job is None:
        print("\nNothing owing — every planned sentence is reviewed or parked.")
        return
    print(f"\nNext up: {job.key}  (attempts so far: {job.attempts})")
    if job.last_failure:
        print(f"  last failure: {job.last_failure}")


if __name__ == "__main__":
    main()
