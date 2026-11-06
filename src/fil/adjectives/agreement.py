"""The rule of agreement: which adjective cell a noun asks for.

An attribute (نَعْت) follows its noun in everything: gender, number, case and definiteness —
بَيْتٌ كَبِيرٌ, الْبَيْتُ الْكَبِيرُ, فِي بَيْتٍ كَبِيرٍ. A predicate (خَبَر) follows its subject
in gender and number only; it is indefinite and nominative (accusative after كَانَ and its
sisters): الْبَيْتُ كَبِيرٌ, كَانَ الْبَيْتُ كَبِيرًا. A plural of people takes the adjective's
plural of the same gender (رِجَالٌ كِبَارٌ); a plural of things takes the feminine singular
(بُيُوتٌ كَبِيرَةٌ). A dual takes the dual of its gender.

Pure.
"""

from __future__ import annotations

from dataclasses import dataclass

from fil.nouns.model import ACCUSATIVE, CONSTRUCT, DEFINITE, FEMININE, INDEFINITE, NOMINATIVE, PLURAL, SINGULAR, Cell


@dataclass(frozen=True)
class NounReading:
    """A noun as it stands in a sentence: one cell of its table, its gender, whether it names people."""

    gender: str
    cell: Cell
    is_human: bool = False


@dataclass(frozen=True)
class AdjectiveReading:
    gender: str
    cell: Cell


def agreeing_gender_number(noun: NounReading) -> tuple[str, str]:
    """The adjective's gender and number for this noun, in attribute and predicate alike."""
    if noun.cell.number == PLURAL and not noun.is_human:
        return FEMININE, SINGULAR
    return noun.gender, noun.cell.number


def is_attribute(adjective: AdjectiveReading, noun: NounReading) -> bool:
    """بَيْتٌ كَبِيرٌ: the same gender and number (by the rule), case and definiteness."""
    return ((adjective.gender, adjective.cell.number) == agreeing_gender_number(noun)
            and adjective.cell.case == noun.cell.case
            and adjective.cell.state == _definiteness(noun.cell.state))


def is_predicate(adjective: AdjectiveReading, subject: NounReading, after_kana: bool = False) -> bool:
    """الْبَيْتُ كَبِيرٌ: a nominative subject, the adjective indefinite in its predicate case."""
    return ((adjective.gender, adjective.cell.number) == agreeing_gender_number(subject)
            and subject.cell.case == NOMINATIVE
            and adjective.cell.state == INDEFINITE
            and adjective.cell.case == (ACCUSATIVE if after_kana else NOMINATIVE))


def _definiteness(state: str) -> str:
    """A noun made definite by what follows it (بَيْتُهُ) takes the definite adjective (بَيْتُهُ الْكَبِيرُ)."""
    return DEFINITE if state in (DEFINITE, CONSTRUCT) else INDEFINITE
