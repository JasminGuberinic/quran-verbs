"""Prijedlog + padež / Preposition + case — a preposition as the Quran says it before a noun: which
ending does the noun take?

Built from the noun cards' Quranic forms: the corpus places the noun right after a preposition
written as a word of its own (فِي، عَلَى، مِنْ، إِلَى، عَنْ) and reads it genitive, with the article or
nunation and nothing attached. The options are that noun's own table cells of the same number and
definiteness in the three cases — the nominative and accusative can never follow a preposition, so
they are wrong by rule, and a cell spelled like the genitive (a diptote's or a sound plural's
accusative) is never offered beside it. All three are shown in one style, so the Quran's own
spelling of the right one gives nothing away; after answering, the learner hears and sees the form
the Quran says, where, and how it is said in Bosnian (u kući, na zemlji) with the Bosnian case.

Pure.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from fil.exercises.model import PREPOSITION, Bilingual, Exercise, Option
from fil.exercises.text import in_one_style, same_spelling
from fil.nouns.model import ACCUSATIVE, GENITIVE, NOMINATIVE, STATES
from fil.nouns.spelling import standalone

MIN_OPTIONS = 3


@dataclass(frozen=True)
class QuranicForm:
    """A noun as the Quran says it after a preposition."""

    preposition: str             # فِي
    arabic: str                  # ٱلْأَرْضِ, as the Quran writes it
    number: str
    state: str
    case: str
    reference: str               # where the Quran first says it
    count: int
    sound: str | None
    gloss: Bilingual             # na zemlji / on the earth
    bosnian_case: str | None     # the case the Bosnian rendering takes (fil.nouns.bosnian: "L")


@dataclass(frozen=True)
class TableRow:
    """One row of a noun's case table: a number (a second plural is a row of its own), its forms."""

    number: str
    cells: Mapping[tuple[str, str], str]               # (state, case) → the form


@dataclass(frozen=True)
class NounForms:
    word: str                                          # "noun:ard"
    rows: tuple[TableRow, ...]
    forms: tuple[QuranicForm, ...]


def preposition_exercises(nouns: Sequence[NounForms], per_noun: int = 2) -> list[Exercise]:
    """At most `per_noun` exercises a noun, its most frequent forms first, one per preposition and number."""
    return [exercise for noun in nouns for exercise in _of_noun(noun, per_noun)]


def _of_noun(noun: NounForms, per_noun: int) -> list[Exercise]:
    built: list[Exercise] = []
    asked: set[tuple[str, str]] = set()
    for form in sorted(noun.forms, key=lambda found: -found.count):
        if len(built) == per_noun:
            break
        if (form.preposition, form.number) in asked:
            continue
        exercise = _exercise(noun, form)
        if exercise:
            built.append(exercise)
            asked.add((form.preposition, form.number))
    return built


def _exercise(noun: NounForms, form: QuranicForm) -> Exercise | None:
    if form.case != GENITIVE or form.state not in STATES:
        return None
    row = _row_saying(noun.rows, form)
    if row is None:
        return None       # the table does not hold the Quran's form: nothing to ask that we can vouch for
    answer = row.cells[(form.state, GENITIVE)]
    wrong = [text for case in (NOMINATIVE, ACCUSATIVE) if (text := row.cells.get((form.state, case)))
             and not same_spelling(text, answer)]
    if len(wrong) < MIN_OPTIONS - 1 or same_spelling(*wrong):
        return None
    slug = noun.word.split(":", 1)[1]
    facts = {"case": GENITIVE, **({"bosnianCase": form.bosnian_case} if form.bosnian_case else {})}
    return Exercise(kind=PREPOSITION, key=f"{slug}-{noun.forms.index(form) + 1}",
                    words=(noun.word,), lead=form.preposition,
                    options=(Option(True, arabic=in_one_style(answer)), *(Option(False, arabic=in_one_style(text)) for text in wrong)),
                    reference=form.reference, answer_word=f"{form.preposition} {form.arabic}", answer_sound=form.sound,
                    gloss=form.gloss, facts=facts)


def _row_saying(rows: Sequence[TableRow], form: QuranicForm) -> TableRow | None:
    """The row whose genitive of the form's definiteness is the form itself."""
    said = standalone(form.arabic)
    return next((row for row in rows if row.number == form.number
                 and same_spelling(row.cells.get((form.state, GENITIVE), ""), said)), None)
