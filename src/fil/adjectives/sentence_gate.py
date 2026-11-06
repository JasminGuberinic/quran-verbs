"""The gate an adjective's practice sentence must pass: the adjective agrees with its noun.

Each sentence shows one use (ROLES): an attribute of a masculine singular noun, of a
feminine singular noun, a predicate, or an adjective agreeing with a plural (or dual) noun.
The analyzer cannot check endings, so both words are held to tables instead, as for the
nouns (fil.nouns.sentence_gate): the adjective must be a cell of its own table, the noun it
describes a cell of one of our studied nouns' tables — letter for letter, vowel for vowel —
and the two cells must agree by the rule (fil.adjectives.agreement): an attribute stands
right after its noun, a predicate after its nominative subject (accusative after كَانَ).

The other layers are the verbs' and nouns' (fil.examples): every word analyzable, every gloss
one the lexicon gives. Results are recorded in ExampleChecks, read for an adjective:
verb_root = "the target is this adjective", verb_form = "it agrees with its noun in the role".

Pure: the analyzer and the tables are passed in.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from fil.adjectives.agreement import AdjectiveReading, NounReading, is_attribute, is_predicate
from fil.examples import Analyze, Example, ExampleChecks, ExampleWord, GlossExceptions, gloss_check
from fil.nouns.model import CONSTRUCT, DUAL, FEMININE, MASCULINE, NOMINATIVE, PLURAL, SINGULAR, Cell
from fil.nouns.sentence_gate import target_cell
from fil.nouns.spelling import skeleton, spelling_key

MASCULINE_ROLE, FEMININE_ROLE, PREDICATE, PLURAL_ROLE = "masculine", "feminine", "predicate", "plural"
ROLES = (MASCULINE_ROLE, FEMININE_ROLE, PREDICATE, PLURAL_ROLE)
CHECKED_BY = "adjective and noun tables"

# كَانَ and the sisters a practice sentence uses, by their letters: the predicate turns accusative.
KANA_FORMS = frozenset({"كان", "كانت", "كانوا", "كانتا", "كانا", "اصبح", "اصبحت", "اصبحوا", "صار", "صارت",
                        "صاروا", "ليس", "ليست", "ليسوا", "يكون", "تكون", "يكونون", "ظل", "ظلت", "بات", "باتت"})
_COORDINATING = ("", "وَ", "فَ")   # an adjective may be joined by "and"; never governed by a preposition

AdjectiveIndex = Mapping[str, tuple[tuple[str, Cell], ...]]   # spelling key → (gender, cell) of the adjective
NounIndex = Mapping[str, tuple[NounReading, ...]]              # spelling key → every studied noun cell spelled so


@dataclass(frozen=True)
class _Found:
    readings: tuple[AdjectiveReading, ...]
    proclitic: str


def adjective_index(cells: Sequence[tuple[str, Cell, str]]) -> dict[str, tuple[tuple[str, Cell], ...]]:
    """(gender, cell, text) triples → the lookup the gate uses."""
    index: dict[str, tuple[tuple[str, Cell], ...]] = {}
    for gender, cell, text in cells:
        key = spelling_key(text)
        index[key] = (*index.get(key, ()), (gender, cell))
    return index


def checked(example: Example, role: str, adjectives: AdjectiveIndex, nouns: NounIndex, analyze: Analyze,
            gloss_exceptions: GlossExceptions | None = None) -> Example:
    return replace(example, checks=check_sentence(example, role, adjectives, nouns, analyze, gloss_exceptions))


def check_sentence(example: Example, role: str, adjectives: AdjectiveIndex, nouns: NounIndex, analyze: Analyze,
                   gloss_exceptions: GlossExceptions | None = None) -> ExampleChecks:
    if role not in ROLES:
        raise ValueError(f"unknown role {role!r}; one of {', '.join(ROLES)}")
    position = next((index for index, word in enumerate(example.words) if word.is_target), None)
    if position is None:
        return ExampleChecks(verb_root=False, verb_form=None, all_words_valid=False)
    target = example.words[position]
    found = _adjective(target.arabic, adjectives)
    analyses = {word: analyze(word.arabic) for word in example.words}
    agreement, conflicts, by_exception = gloss_check(analyses, gloss_exceptions or {})
    return ExampleChecks(
        verb_root=found is not None,
        verb_form=found is not None and agrees_in_role(role, found.readings, example.words, position, nouns),
        all_words_valid=all(found_analyses or (word is target and found) for word, found_analyses in analyses.items()),
        gloss_agreement=agreement, gloss_conflicts=conflicts,
        verb_form_by=CHECKED_BY if found else "", glossed_by_exception=by_exception)


def _adjective(word: str, adjectives: AdjectiveIndex) -> _Found | None:
    found = target_cell(word, adjectives)
    if found is None or found[1] not in _COORDINATING:
        return None
    readings, proclitic = found
    return _Found(tuple(AdjectiveReading(gender, cell) for gender, cell in readings), proclitic)


def agrees_in_role(role: str, readings: Sequence[AdjectiveReading], words: Sequence[ExampleWord], position: int,
                   nouns: NounIndex) -> bool:
    """Does some reading of the adjective agree, as the role asks, with the noun it describes?"""
    attributes = [(adjective, noun) for adjective in readings for noun in _noun_before(words, position, nouns)
                  if is_attribute(adjective, noun)]
    predicates = [(adjective, subject) for adjective in readings for subject in _subjects(words, position, nouns)
                  if is_predicate(adjective, subject, _after_kana(words, position))]
    if role == MASCULINE_ROLE:
        return any(_is(adjective, MASCULINE, SINGULAR) and noun.cell.number == SINGULAR for adjective, noun in attributes)
    if role == FEMININE_ROLE:
        return any(_is(adjective, FEMININE, SINGULAR) and noun.cell.number == SINGULAR for adjective, noun in attributes)
    if role == PREDICATE:
        return bool(predicates)
    return any(noun.cell.number in (PLURAL, DUAL) for _adjective_reading, noun in (*attributes, *predicates))


def _is(adjective: AdjectiveReading, gender: str, number: str) -> bool:
    return adjective.gender == gender and adjective.cell.number == number


def _noun_before(words: Sequence[ExampleWord], position: int, nouns: NounIndex) -> tuple[NounReading, ...]:
    """The noun an attribute describes stands right before it — never a noun in construct, whose
    attribute follows its possessor (بَيْتُ الرَّجُلِ الْكَبِيرُ), which a table cannot tell apart."""
    if position == 0:
        return ()
    return tuple(reading for reading in _noun_readings(words[position - 1].arabic, nouns) if reading.cell.state != CONSTRUCT)


def _subjects(words: Sequence[ExampleWord], position: int, nouns: NounIndex) -> tuple[NounReading, ...]:
    """The subject of a predicate: the nearest studied noun before it that can be nominative —
    a possessor (اسْمُ الشَّاعِرِ) or a noun after a preposition (الطَّرِيقُ إِلَى الْقَرْيَةِ) is passed over."""
    for word in reversed(words[:position]):
        readings = tuple(reading for reading in _noun_readings(word.arabic, nouns) if reading.cell.case == NOMINATIVE)
        if readings:
            return readings
    return ()


def _noun_readings(word: str, nouns: NounIndex) -> tuple[NounReading, ...]:
    found = target_cell(word, nouns)
    return found[0] if found else ()


def _after_kana(words: Sequence[ExampleWord], position: int) -> bool:
    return any(skeleton(word.arabic) in KANA_FORMS for word in words[:position])
