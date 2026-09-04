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
    claimed_by: str = ""         # which worker is on it right now …
    claimed_until: str = ""      # … and when that claim goes stale (ISO-8601, UTC)

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


# How many drafts one cell may consume before we stop spending on it. Bounded on
# purpose: an unbounded repair loop is how an agent burns a budget and then converges
# on something plausible but wrong. Three tries, then a person decides.
MAX_ATTEMPTS = 3

# A parked job whose reason begins with this is not a dead end — it is queued for the one
# worker the pipeline cannot replace.
NEEDS_HUMAN = "needs a human"


def needs_human(job: Job) -> bool:
    """Whether this job is parked waiting on a person rather than on us."""
    return job.state == PARKED and job.reason.startswith(NEEDS_HUMAN)


def after_failure(job: Job, failure: str, max_attempts: int = MAX_ATTEMPTS) -> Job:
    """Send a failed job back for another draft, or park it once its budget is spent.

    The failure is recorded either way, so the next attempt starts from what went wrong
    rather than from nothing — and a parked job says how many tries it cost.
    """
    if job.attempts >= max_attempts:
        return advance(
            job, PARKED, failure=failure,
            reason=f"gave up after {job.attempts} attempt(s): {failure}",
        )
    return advance(job, DRAFTED, failure=failure)


def reopened_after_refusal(job: Job, failure: str) -> Job:
    """Reopen a cell because a reader refused its sentence.

    That the refusal HAPPENED is recorded in the journal, not here — this row will be
    overwritten many times, and history must outlive it (see fil.journal).
    """
    return recognise(job, DRAFTED, failure=failure)


# How long a worker may hold a job before another may take it. Long enough for a slow
# drafting pass, short enough that a session which died does not freeze a cell forever.
LEASE_SECONDS = 900


def claim(job: Job, worker: str, until: str) -> Job:
    """Mark a job as being worked on until `until`, so a second worker skips it.

    Two agents running against the same repo will otherwise pick the same "next" job and
    each write a sentence for it — one of which is silently discarded. The claim is a lease
    rather than a lock on purpose: nothing here can tell whether a worker died, so a stale
    claim simply expires instead of needing a human to release it.
    """
    if job.claimed_by and job.claimed_until > until:
        raise TransitionError(f"{job.key} is already claimed by {job.claimed_by}")
    return replace(job, claimed_by=worker, claimed_until=until)


def released(job: Job) -> Job:
    """Drop the claim — the work is done, or the worker is walking away from it."""
    return replace(job, claimed_by="", claimed_until="")


def is_claimed(job: Job, now: str) -> bool:
    """Whether someone else is on it right now (an expired claim counts as free)."""
    return bool(job.claimed_by) and job.claimed_until > now


def recognise(job: Job, state: str, note: str = "", failure: str = "") -> Job:
    """Set a job's state from evidence outside the agenda, bypassing the lifecycle.

    Work done before the agenda existed — or by someone else — is not a transition we can
    replay; refusing to record it would only make the agenda ask for sentences that are
    already written. This is the one deliberate door around `advance`, and it exists so the
    agenda can be told the truth rather than kept tidy.
    """
    if state not in _STATES:
        raise TransitionError(f"unknown state {state!r}")
    return replace(job, state=state, attempts=max(job.attempts, 1), last_failure=failure, reason=note)


def open_jobs(jobs: Iterable[Job], now: str = "") -> list[Job]:
    """The jobs still owing work and free to take, neediest first.

    `now` lets the caller exclude jobs another worker holds a live claim on; passing nothing
    ignores claims entirely, which is what a single-worker run wants.
    """
    available = (job for job in jobs if job.is_open and not (now and is_claimed(job, now)))
    return sorted(available, key=lambda job: (job.attempts, job.key))


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
