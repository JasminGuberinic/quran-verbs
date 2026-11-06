"""The card's agreement section: this adjective with our nouns, one example per rule.

    indefinite    بَيْتٌ كَبِيرٌ               a big house                velika kuća
    definite      الْبَيْتُ الْكَبِيرُ          the big house              velika kuća
    feminine      شَجَرَةٌ كَبِيرَةٌ            a big tree                 veliko drvo
    humanPlural   رِجَالٌ كِبَارٌ               big men                    veliki ljudi
    thingPlural   بُيُوتٌ كَبِيرَةٌ             big houses                 velike kuće
    predicate     الْبَيْتُ كَبِيرٌ             The house is big.          Kuća je velika.
    elative       الْبَيْتُ أَكْبَرُ مِنَ الشَّجَرَةِ   The house is bigger than the tree.   Kuća je veća od drveta.

Every Arabic word is a cell of a table (in its standard spelling, fil.nouns.spelling.imlai) — the adjective's own, the nouns' — so each example
is right by construction; English and Bosnian follow by rule (fil.adjectives.english,
fil.adjectives.bosnian), the Bosnian adjective agreeing with the Bosnian noun's gender. An
example whose cell is empty is left out. The examples are read by the blind reviewer before a
learner sees them: by construction they are grammatical, not necessarily natural.

Pure.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fil.adjectives import bosnian, english
from fil.adjectives.model import AdjectiveMeaning, AdjectiveTable
from fil.nouns import bosnian as bosnian_nouns
from fil.nouns.bosnian import BosnianNoun
from fil.nouns.english import EnglishNoun
from fil.nouns.spelling import imlai
from fil.nouns.model import DEFINITE, FEMININE, GENITIVE, INDEFINITE, NOMINATIVE, PLURAL, SINGULAR

INDEFINITE_EXAMPLE, DEFINITE_EXAMPLE, FEMININE_EXAMPLE = "indefinite", "definite", "feminine"
HUMAN_PLURAL, THING_PLURAL, PREDICATE, ELATIVE = "humanPlural", "thingPlural", "predicate", "elative"
KINDS = (INDEFINITE_EXAMPLE, DEFINITE_EXAMPLE, FEMININE_EXAMPLE, HUMAN_PLURAL, THING_PLURAL, PREDICATE, ELATIVE)
_MIN_BEFORE_ARTICLE = "مِنَ"
_BOSNIAN_NUMBERS = {SINGULAR: bosnian_nouns.SINGULAR, PLURAL: bosnian_nouns.PLURAL}


@dataclass(frozen=True)
class DescribedNoun:
    """One of our nouns as the examples need it."""

    gender: str                                     # the Arabic gender: M, F
    text: Callable[[str, str, str], str | None]     # (number, state, case) → its table's cell
    english: EnglishNoun
    bosnian: BosnianNoun


@dataclass(frozen=True)
class AgreementExample:
    kind: str
    arabic: str
    en: str
    bs: str


def examples(meaning: AdjectiveMeaning, table: AdjectiveTable, nouns: dict[str, DescribedNoun],
             elative: str | None = None) -> list[AgreementExample]:
    """The examples this adjective's table and nouns can make, in KINDS order. `nouns` maps the
    meaning's noun keys to the nouns; `elative` is the comparative's indefinite nominative (أَكْبَرُ)."""
    described = meaning.nouns
    built = [
        _attribute(INDEFINITE_EXAMPLE, meaning, table, nouns[described.masculine], SINGULAR, INDEFINITE),
        _attribute(DEFINITE_EXAMPLE, meaning, table, nouns[described.masculine], SINGULAR, DEFINITE),
        _attribute(FEMININE_EXAMPLE, meaning, table, nouns[described.feminine], SINGULAR, INDEFINITE),
        _attribute(HUMAN_PLURAL, meaning, table, nouns[described.human_plural], PLURAL, INDEFINITE, is_human=True)
        if described.human_plural else None,
        _attribute(THING_PLURAL, meaning, table, nouns[described.thing_plural], PLURAL, INDEFINITE)
        if described.thing_plural else None,
        _predicate(meaning, table, nouns[described.masculine]),
        _comparison(meaning, elative, nouns[described.masculine], nouns[described.feminine]),
    ]
    return [example for example in built if example]


def _attribute(kind: str, meaning: AdjectiveMeaning, table: AdjectiveTable, noun: DescribedNoun, number: str,
               state: str, is_human: bool = False) -> AgreementExample | None:
    gender, adjective_number = _agreeing(noun.gender, number, is_human)
    noun_text = _standard(noun.text(number, state, NOMINATIVE))
    adjective_text = _standard(table.text(gender, adjective_number, state, NOMINATIVE))
    bosnian_noun = _bosnian_noun(noun.bosnian, number)
    if not (noun_text and adjective_text and bosnian_noun):
        return None
    word, bosnian_gender, bosnian_number = bosnian_noun
    adjective_bs = bosnian.attribute(meaning.bs_long, bosnian_gender, bosnian_number,
                                     short_form=meaning.bs_short, is_definite=state == DEFINITE)
    return AgreementExample(kind, f"{noun_text} {adjective_text}",
                            english.attribute(meaning.en_first, noun.english, number, state == DEFINITE),
                            f"{adjective_bs} {word}")


def _predicate(meaning: AdjectiveMeaning, table: AdjectiveTable, noun: DescribedNoun) -> AgreementExample | None:
    subject = _standard(noun.text(SINGULAR, DEFINITE, NOMINATIVE))
    adjective_text = _standard(table.text(noun.gender, SINGULAR, INDEFINITE, NOMINATIVE))
    bosnian_noun = _bosnian_noun(noun.bosnian, SINGULAR)
    if not (subject and adjective_text and bosnian_noun):
        return None
    word, gender, _number = bosnian_noun
    adjective_bs = bosnian.predicate(meaning.bs_long, meaning.bs_short, gender, bosnian_nouns.SINGULAR)
    return AgreementExample(PREDICATE, f"{subject} {adjective_text}", english.predicate(meaning.en_first, noun.english, SINGULAR),
                            f"{_capitalised(word)} {bosnian.copula(bosnian_nouns.SINGULAR)} {adjective_bs}.")


def _comparison(meaning: AdjectiveMeaning, elative: str | None, subject: DescribedNoun,
                other: DescribedNoun) -> AgreementExample | None:
    if not (elative and meaning.elative):
        return None
    first, second = _standard(subject.text(SINGULAR, DEFINITE, NOMINATIVE)), _standard(other.text(SINGULAR, DEFINITE, GENITIVE))
    bosnian_subject = _bosnian_noun(subject.bosnian, SINGULAR)
    other_genitive = other.bosnian.cell(bosnian_nouns.SINGULAR, bosnian_nouns.GENITIVE)
    if not (first and second and bosnian_subject and other_genitive):
        return None
    word, gender, _number = bosnian_subject
    comparative = bosnian.attribute(meaning.elative.bs, gender, bosnian_nouns.SINGULAR)
    return AgreementExample(ELATIVE, f"{first} {elative} {_MIN_BEFORE_ARTICLE} {second}",
                            english.comparison(meaning.elative.en, subject.english, other.english),
                            f"{_capitalised(word)} je {comparative} od {other_genitive}.")


def _agreeing(gender: str, number: str, is_human: bool) -> tuple[str, str]:
    if number == PLURAL and not is_human:
        return FEMININE, SINGULAR
    return gender, number


def _bosnian_noun(noun: BosnianNoun, number: str) -> tuple[str, str, str] | None:
    """The Bosnian noun's nominative and the gender and number an adjective agrees with
    ("radosna djeca": a collective singular agrees in the feminine singular); None for a noun
    whose Bosnian number is plural where the Arabic one is singular (a collective's "deve")."""
    wanted = _BOSNIAN_NUMBERS[number]
    word, agreement = noun.cell(wanted, bosnian_nouns.NOMINATIVE), noun.agreement(wanted)
    if not word or not agreement or wanted in noun.plural_numbers:
        return None
    return word, *agreement


def _standard(text: str | None) -> str | None:
    """A learner reads the examples as modern Arabic: a Quranic cell in its imlāʾī spelling."""
    return imlai(text) if text else None


def _capitalised(text: str) -> str:
    return text[:1].upper() + text[1:]

