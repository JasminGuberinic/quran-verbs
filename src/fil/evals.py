"""Numbers that say whether a change to the factory actually helped.

We already produced one such number by accident: before the word bank existed, six drafted
sentences carried two defects; after it, ten passed on the first attempt. That is the kind
of evidence this module makes routine, because without it "the pipeline feels better" is
just a feeling.

Five measures, each answering one question:

  first_try_pass_rate      did grounding the drafter actually work?
  attempts_per_accepted    is the repair loop converging, or thrashing?
  critic_rejection_rate    how much gets past the mechanical gate and is caught by a
                           reader — the honest measure of the gate's real strength. It is
                           counted on the AGENDA, because repairing a refused sentence
                           replaces it: read the store alone and the pipeline would grade
                           itself on evidence it had just erased.
  parked                   where the pipeline hurts enough that we stopped
  illustrated_cells        what a learner can actually be shown

The most important of them is the third. A gate that never lets anything through to be
rejected is either perfect or untested, and we should assume the second.

Separately, a GOLDEN SET pins the gate itself. It holds sentences whose verdict we already
know — including the two that were genuinely wrong (a gloss the lexicon does not support,
and a form that is morphologically perfect but not idiomatic) — so that a future "cleanup"
that stops catching them fails loudly instead of quietly shipping them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from fil.agenda import CHECKED, PARKED, REVIEWED, Job
from fil.examples import Example


@dataclass(frozen=True)
class Metrics:
    """The five numbers, with the counts they were computed from.

    A rate is None when nothing has happened yet — reporting 0.0% for "no data" would
    read as a failure rather than as silence.
    """

    drafted_jobs: int
    first_try_pass_rate: float | None      # % of gated jobs that passed on attempt one
    attempts_per_accepted: float | None    # mean drafts spent per reviewed sentence
    reader_refusals: int                   # times a reader has ever refused a sentence
    critic_rejection_rate: float | None    # refusals as a share of all verdicts given
    parked: int
    illustrated_cells: int                 # distinct (verb, cell) a learner can be shown


def measure(jobs: Iterable[Job], examples: Iterable[Example]) -> Metrics:
    """Compute the headline numbers from the agenda and the sentences themselves (pure)."""
    jobs = list(jobs)
    examples = list(examples)

    gated = [job for job in jobs if job.state in (CHECKED, REVIEWED)]
    accepted = [job for job in jobs if job.state == REVIEWED]
    # Refusals are counted on the AGENDA, not in the store: a repaired sentence replaces
    # the one that was refused, so reading the store alone would report that nothing was
    # ever caught — the pipeline would grade itself on the evidence it had just erased.
    refusals = sum(job.refusals for job in jobs)
    standing = [example for example in examples if example.independently_reviewed]

    return Metrics(
        drafted_jobs=sum(job.attempts > 0 for job in jobs),
        first_try_pass_rate=_percent(sum(job.attempts <= 1 for job in gated), len(gated)),
        attempts_per_accepted=_mean(job.attempts for job in accepted) if accepted else None,
        reader_refusals=refusals,
        critic_rejection_rate=_percent(refusals, refusals + len(standing)),
        parked=sum(job.state == PARKED for job in jobs),
        illustrated_cells=len({
            (example.tense, example.pronoun) for example in examples
            if example.is_shippable and example.tense and example.pronoun
        }),
    )


@dataclass(frozen=True)
class GoldenCase:
    """A sentence whose verdict we already know, and why it is in the set."""

    example: Example
    expect_gate_passes: bool
    because: str


@dataclass(frozen=True)
class GoldenResult:
    """What the gate said about a golden case this time."""

    arabic: str
    expected: bool
    actual: bool
    because: str

    @property
    def holds(self) -> bool:
        return self.expected == self.actual


def check_golden(cases: Iterable[GoldenCase], root_of, check) -> list[GoldenResult]:
    """Re-run the gate over the golden set; a differing verdict is a regression.

    `check` is injected (the real gate needs a morphological analyzer, which is heavy), so
    this stays a pure comparison and the caller decides what to run it with.
    """
    results = []
    for case in cases:
        checks = check(case.example, root_of(case.example))
        results.append(GoldenResult(
            arabic=case.example.arabic,
            expected=case.expect_gate_passes,
            actual=checks.passed,
            because=case.because,
        ))
    return results


def _percent(part: int, whole: int) -> float | None:
    return round(100.0 * part / whole, 1) if whole else None


def _mean(values) -> float:
    values = list(values)
    return round(sum(values) / len(values), 2)
