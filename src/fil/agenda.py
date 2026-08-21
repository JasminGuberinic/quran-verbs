"""What the factory still owes: one job per sentence we intend a verb to have.

Until now the workflow lived in a conversation. Nothing remembered which verbs were
already illustrated, which drafts had failed the gate and why, or how many times we had
already tried — so every session started from zero and quietly repeated work that had
already failed. This module is that memory, and it is deliberately dull: a job, a state,
a reason.

A job is one (verb, tense, pronoun) — the cell a sentence is meant to demonstrate. It
moves through:

    todo ──▶ drafted ──▶ checked ──▶ reviewed        the happy path
              │            │
              └────────────┴──▶ parked               needs a human, or we gave up

`checked` means the mechanical gate passed; `reviewed` means a reader approved it too.
Nothing here decides anything about Arabic — it only records what happened, so the state
transitions stay pure and testable while the sentences themselves live in the example
store.

Two properties make this safe to drive from an agent. Jobs are **idempotent**: recording
the same outcome twice is not an error and never double-counts, so a crashed or abandoned
session costs nothing. And a failure is always **recorded with its reason and attempt
count**, so "we tried this and it did not work" survives the session that discovered it.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

TODO = "todo"
DRAFTED = "drafted"
CHECKED = "checked"
REVIEWED = "reviewed"
PARKED = "parked"

_STATES = (TODO, DRAFTED, CHECKED, REVIEWED, PARKED)

# Which states a job may move to. Terminal states accept nothing further, so a reviewed
# sentence cannot be quietly re-opened by a later run.
_ALLOWED: dict[str, tuple[str, ...]] = {
    TODO: (DRAFTED, PARKED),
    DRAFTED: (CHECKED, DRAFTED, PARKED),   # DRAFTED→DRAFTED is a repair attempt
    CHECKED: (REVIEWED, DRAFTED, PARKED),  # a reader may send it back for repair
    REVIEWED: (),
    PARKED: (TODO,),                       # only a deliberate un-park revives it
}


@dataclass(frozen=True)
class Job:
    """One sentence the factory owes, and everything we know about its fate."""

    root: str
    form: int
    tense: str
    pronoun: str
    state: str = TODO
    attempts: int = 0            # how many drafts this job has consumed
    last_failure: str = ""       # why the most recent attempt did not stick
    reason: str = ""             # why it is parked, when it is

    @property
    def key(self) -> str:
        """Stable identity — the same cell always maps to the same job."""
        return f"{self.root}_{self.form}:{self.tense}:{self.pronoun}"

    @property
    def is_open(self) -> bool:
        """Whether the factory still owes work here."""
        return self.state not in (REVIEWED, PARKED)


class TransitionError(ValueError):
    """A move the lifecycle does not allow — raised loudly rather than absorbed."""


def advance(job: Job, state: str, failure: str = "", reason: str = "") -> Job:
    """Move a job to `state`, recording why if something went wrong.

    Re-recording the state a job is already in is accepted and changes nothing (jobs are
    idempotent), except for a repeated draft, which counts as another attempt.
    """
    if state not in _STATES:
        raise TransitionError(f"unknown state {state!r}")
    if state == job.state and state != DRAFTED:
        return job
    if state not in _ALLOWED[job.state]:
        raise TransitionError(f"{job.key}: cannot go {job.state} → {state}")

    return replace(
        job,
        state=state,
        attempts=job.attempts + (state == DRAFTED),
        last_failure=failure,
        reason=reason or (job.reason if state == PARKED else ""),
    )


def recognise(job: Job, state: str, note: str = "") -> Job:
    """Set a job's state from evidence outside the agenda, bypassing the lifecycle.

    Work done before the agenda existed — or by someone else — is not a transition we can
    replay; refusing to record it would only make the agenda ask for sentences that are
    already written. This is the one deliberate door around `advance`, and it exists so the
    agenda can be told the truth rather than kept tidy.
    """
    if state not in _STATES:
        raise TransitionError(f"unknown state {state!r}")
    return replace(job, state=state, attempts=max(job.attempts, 1), last_failure="", reason=note)


def open_jobs(jobs: Iterable[Job]) -> list[Job]:
    """The jobs still owing work, neediest first — fewest attempts before most."""
    return sorted((job for job in jobs if job.is_open), key=lambda job: (job.attempts, job.key))


def plan_for(root: str, form: int, cells: Iterable[tuple[str, str]], existing: Iterable[Job]) -> list[Job]:
    """The jobs a verb needs for the given cells, leaving any that already exist alone.

    This is what makes adding verbs cheap: hand it the cells worth illustrating and it
    returns only what is genuinely new, so re-planning is safe.
    """
    known = {job.key for job in existing}
    fresh = [Job(root=root, form=form, tense=tense, pronoun=pronoun) for tense, pronoun in cells]
    return [job for job in fresh if job.key not in known]


def tally(jobs: Iterable[Job]) -> dict[str, int]:
    """How many jobs sit in each state — the headline the agent reports."""
    counts = {state: 0 for state in _STATES}
    for job in jobs:
        counts[job.state] += 1
    return counts
