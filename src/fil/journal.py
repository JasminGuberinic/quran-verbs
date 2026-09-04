"""What happened, in the order it happened, and never edited afterwards.

This module exists because of a bug worth remembering. The factory measured how often a
reader caught something the machine had missed — and it measured it by reading the current
sentences. But repairing a refused sentence REPLACES it, so the moment a defect was fixed,
the evidence that it had ever existed disappeared. The pipeline reported a flawless 0%
while five real defects had just been found and repaired.

The mistake was architectural, not arithmetical: **state was being used as history.** A
store that holds "what is true now" cannot answer "what happened", and every attempt to
squeeze the second out of the first produces numbers that flatter whoever is asking.

So the two are separated. `fil.agenda` holds current state — one row per cell, overwritten
as it moves. This holds the record — append-only, never rewritten, one line per thing that
occurred. State is a projection of history and can always be rebuilt from it; history can
never be rebuilt from state.

Events carry their own timestamp rather than reading a clock, so recording is pure and a
test can lay out a sequence of events by hand.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

# The things worth remembering. Deliberately few: an event log grows forever, so each kind
# must answer a question somebody will actually ask.
PLANNED = "planned"        # a cell was added to the agenda
DRAFTED = "drafted"        # a sentence was written for it
GATED = "gated"            # the mechanical checks ran, and what they said
JUDGED = "judged"          # a reader gave a verdict, and whether they were independent
PARKED = "parked"          # we stopped, and why
HANDED_OVER = "handed_over"  # a person was asked for something

_KINDS = (PLANNED, DRAFTED, GATED, JUDGED, PARKED, HANDED_OVER)


@dataclass(frozen=True)
class Event:
    """One thing that happened. Immutable, and never deleted once written."""

    at: str            # ISO-8601, supplied by the caller — this module owns no clock
    kind: str
    subject: str       # the job key, or the sentence it concerns
    detail: str        # what happened, in a sentence a person can read
    by: str = ""       # who caused it, when that matters (a model, a person, the engine)
    outcome: bool | None = None   # for GATED/JUDGED: did it pass, was it approved
    independent: bool | None = None  # for JUDGED: had the reader no hand in the sentence

    def __post_init__(self) -> None:
        if self.kind not in _KINDS:
            raise ValueError(f"unknown event kind {self.kind!r}")


def refusals(events: Iterable[Event]) -> list[Event]:
    """Every time a reader refused a sentence — the evidence a repair would have erased."""
    return [event for event in events if event.kind == JUDGED and event.outcome is False]


def independent_verdicts(events: Iterable[Event]) -> list[Event]:
    """Verdicts from a reader who had no hand in the sentence (the only ones that count)."""
    return [event for event in events if event.kind == JUDGED and event.independent]


def for_subject(events: Iterable[Event], subject: str) -> list[Event]:
    """Everything that ever happened to one cell — its whole story, in order."""
    return [event for event in events if event.subject == subject]
