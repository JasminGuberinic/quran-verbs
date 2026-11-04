"""Split one Quranic word into what a gloss is built from: proclitics, a verb cell, objects.

The corpus already segments every word (وَ + قَالُ + وا۟ + هُ); the verb itself, with its
documented corrections applied, arrives as a VerbOccurrence. What is left is to name the
proclitics before it and to check that nothing after it is beyond the rules — an energic
nūn is understood only where an emphatic لَ makes it an oath ("they will surely say").

Anything unexpected raises CannotCompose with a short reason: a form we cannot read with
certainty keeps its grammar label, which is never wrong.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from fil.corpus.parse import Segment, VerbOccurrence

# Proclitic names, in the order they may stand.
AND = "and"            # وَ (CONJ, REM)
SO = "so"              # فَ (CONJ, REM, RSLT)
EMPHATIC = "emphatic"  # لَ: "surely"
PURPOSE = "purpose"    # لِ: "so that"
LET = "let"            # لْ / لِ of command: "let him…"
QUESTION = "question"  # أَ / ءَ

TENSES = ("past", "present", "imperative", "future")


class CannotCompose(ValueError):
    """The form holds something the composition rules do not cover; `reason` names it."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason


@dataclass(frozen=True)
class Cell:
    """The verb itself: when, who, in which voice, and to whom."""

    tense: str                      # one of TENSES
    subject: str                    # person-gender-number: "3MS", "1P", "2MP", "3FD"…
    is_passive: bool
    objects: tuple[str, ...] = ()   # attached object pronouns, same notation

    @property
    def code(self) -> str:
        """How the cell is named in the paradigm file: past|act|3MP|3MS."""
        voice = "pass" if self.is_passive else "act"
        return "|".join((self.tense, voice, self.subject, "+".join(self.objects) or "-"))


@dataclass(frozen=True)
class Decomposition:
    proclitics: tuple[str, ...]
    cell: Cell
    mood: str | None                # the corpus's own tag for a present: IND, SUBJ, JUS

    @property
    def morpheme_count(self) -> int:
        """Everything around the stem: proclitics and objects."""
        return len(self.proclitics) + len(self.cell.objects)


def decompose(occurrence: VerbOccurrence, word: Sequence[Segment]) -> Decomposition:
    """The parts of the word `occurrence` stands in (its segments, in order)."""
    before = [segment for segment in word if segment.index < occurrence.segment]
    after = [segment for segment in word if segment.index > occurrence.segment]
    _require_one_verb(before + after)
    proclitics = tuple(_proclitic(segment) for segment in before)
    _require_ordered(proclitics)
    is_energic = any(_is_energic(segment) for segment in after)
    _require_known_suffixes(after)
    tense = _tense(occurrence, proclitics, is_energic)
    subject = pgn(occurrence.person, occurrence.gender, occurrence.number)
    objects = _without_dual_subject(subject, tuple(pgn(*found) for found in occurrence.objects))
    cell = Cell(tense, subject, occurrence.passive, objects)
    return Decomposition(tuple(name for name in proclitics if name != _FUTURE), cell, occurrence.mood)


def pgn(person: int, gender: str | None, number: str) -> str:
    """A person/gender/number triple in the corpus's own notation: 3MP, 1S, 2D."""
    if number == "D" and person == 2:
        return "2D"
    return f"{person}{gender or ''}{number}"


_FUTURE = "future"   # سَ: folded into the cell's tense, never rendered as a word

# (tag, bare letter) → proclitic name. Anything else before a verb is beyond the rules.
_PROCLITICS = {
    ("CONJ", "و"): AND, ("REM", "و"): AND,
    ("CONJ", "ف"): SO, ("REM", "ف"): SO, ("RSLT", "ف"): SO,
    ("EMPH", "ل"): EMPHATIC,
    ("PRP", "ل"): PURPOSE,
    ("IMPV", "ل"): LET,
    ("INTG", "أ"): QUESTION, ("INTG", "ء"): QUESTION,
    ("FUT", "س"): _FUTURE,
}


def _proclitic(segment: Segment) -> str:
    tag = segment.features[0]
    letter = segment.surface[:1]
    name = _PROCLITICS.get((tag, letter))
    if name is None:
        raise CannotCompose("unknown proclitic", f"{segment.surface} {tag}")
    return name


def _require_ordered(proclitics: tuple[str, ...]) -> None:
    """At most a conjunction, then at most one particle: وَلْيَقُولُوا. A question before a
    conjunction (أَوَعَجِبْتُمْ "and are you amazed?") reorders the clause, beyond the rules."""
    conjunctions = [name for name in proclitics if name in (AND, SO)]
    particles = [name for name in proclitics if name not in (AND, SO, _FUTURE)]
    if len(conjunctions) > 1 or len(particles) > 1 or proclitics[:len(conjunctions)] != tuple(conjunctions):
        raise CannotCompose("unknown proclitic order", "+".join(proclitics))


def _require_one_verb(others: Sequence[Segment]) -> None:
    if any(segment.pos == "V" for segment in others):
        raise CannotCompose("two verbs in one word")


def _is_energic(segment: Segment) -> bool:
    return "EMPH" in segment.features and "SUFF" in segment.features


def _require_known_suffixes(after: Sequence[Segment]) -> None:
    for segment in after:
        if not (segment.is_pronoun_suffix or _is_energic(segment)):
            raise CannotCompose("unknown suffix", "|".join(segment.features))


def _without_dual_subject(subject: str, objects: tuple[str, ...]) -> tuple[str, ...]:
    """يُرِيدَا: the corpus tags the verb 3MD and its ending ـا 3D, so the subject's own
    ending was left over as if it were an object ("they two want them two")."""
    if subject in ("3MD", "3FD") and objects[:1] == ("3D",):
        return objects[1:]
    return objects


def _tense(occurrence: VerbOccurrence, proclitics: tuple[str, ...], is_energic: bool) -> str:
    """The cell's tense: سَ and an oath's energic nūn (لَيَقُولُنَّ) both make a present future."""
    if is_energic:
        if occurrence.tense != "present" or EMPHATIC not in proclitics:
            raise CannotCompose("energic without oath")
        return "future"
    if _FUTURE in proclitics:
        return "future"
    return occurrence.tense
