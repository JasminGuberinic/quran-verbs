"""Slaganje pridjeva / Adjective agreement — a noun in a practice sentence: which form of the adjective
agrees with it?

Built from the adjective cards' reviewed practice sentences, where the adjective is an attribute
standing right after its noun; both words are cells of our own checked tables, as the adjective
sentence gate holds them (fil.adjectives.sentence_gate). The right option is the form the sentence
says. A distractor is another cell of the same adjective that agrees with no reading of the noun by
the rule (fil.adjectives.agreement) — and is not a form good Arabic also allows: beside a plural of
things the Quran itself uses plural adjectives too (أَيَّامًا مَعْدُودَاتٍ، سَبْعَ سَمَاوَاتٍ طِبَاقًا), and beside a
broken plural of people the feminine singular, so neither is ever offered as wrong. Distractors
differ from the answer in one thing each where they can: the gender or number, the case, the
definiteness.

Pure: the tables are passed in.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from fil.adjectives.agreement import AdjectiveReading, NounReading, is_attribute
from fil.exercises.cases import SentenceWord
from fil.exercises.model import AGREEMENT, Bilingual, Exercise, Option, Segment
from fil.exercises.text import first_distinct, in_one_style, same_spelling, stable_order
from fil.nouns.model import CONSTRUCT, DUAL, FEMININE, MASCULINE, PLURAL, SINGULAR
from fil.nouns.sentence_gate import target_cell
from fil.nouns.spelling import spelling_key

OPTION_COUNT = 4
MIN_OPTIONS = 3
# The rule that decides the form, as the interface names it.
MASCULINE_RULE, FEMININE_RULE, DUAL_RULE, PEOPLE_RULE, THINGS_RULE = (
    "masculine", "feminine", "dual", "peoplePlural", "thingsPlural")

NounIndex = Mapping[str, tuple[NounReading, ...]]   # spelling key → readings (fil.stages.adjectives.noun_readings)


@dataclass(frozen=True)
class AdjectiveForm:
    """One cell of the adjective's table, with its gender."""

    text: str
    reading: AdjectiveReading


@dataclass(frozen=True)
class AdjectiveSentence:
    word: str                         # "adjective:kabir"
    words: tuple[SentenceWord, ...]
    translation: Bilingual
    forms: tuple[AdjectiveForm, ...]  # the adjective's whole table
    sound: str | None = None


def agreement_exercises(sentences: Sequence[AdjectiveSentence], nouns: NounIndex) -> list[Exercise]:
    return [exercise for exercise in (_exercise(sentence, nouns) for sentence in sentences) if exercise]


def _exercise(sentence: AdjectiveSentence, nouns: NounIndex) -> Exercise | None:
    position = _target_position(sentence.words)
    if not position:
        return None
    said = sentence.words[position].arabic
    answers = [form for form in sentence.forms if same_spelling(form.text, said)]
    noun_readings = _noun_before(sentence.words[position - 1].arabic, nouns)
    pairs = [(form, noun) for form in answers for noun in noun_readings if is_attribute(form.reading, noun)]
    if not pairs:
        return None       # a predicate, or a noun our tables do not read: not an attribute to ask about
    answer, noun = pairs[0]
    distractors = _distractors(sentence, answer, noun_readings)
    if len(distractors) < MIN_OPTIONS - 1:
        return None
    options = (Option(True, arabic=in_one_style(said)), *(Option(False, arabic=in_one_style(form.text)) for form in distractors))
    passage = tuple(Segment(word.arabic, is_marked=index == position - 1, is_blank=index == position)
                    for index, word in enumerate(sentence.words))
    return Exercise(kind=AGREEMENT, key=f"{sentence.word.split(':', 1)[1]}-{_rule(noun)}", words=(sentence.word,),
                    options=options, passage=passage, translation=sentence.translation, answer_word=said,
                    answer_sound=sentence.sound, gloss=sentence.words[position].gloss,
                    facts={"rule": _rule(noun), "case": noun.cell.case, "state": noun.cell.state})


def _target_position(words: Sequence[SentenceWord]) -> int | None:
    positions = [index for index, word in enumerate(words) if word.is_target]
    return positions[0] if len(positions) == 1 else None


def _noun_before(word: str, nouns: NounIndex) -> tuple[NounReading, ...]:
    """Every reading of the word before the adjective as a studied noun — none in construct, whose
    attribute follows its possessor instead."""
    found = target_cell(word, nouns)
    if found is None or found[1]:
        return ()
    return tuple(reading for reading in found[0] if reading.cell.state != CONSTRUCT)


def _distractors(sentence: AdjectiveSentence, answer: AdjectiveForm, nouns: Sequence[NounReading]) -> list[AdjectiveForm]:
    """Cells wrong for every reading of the noun, spelled unlike the answer, one difference each where possible."""
    by_spelling: dict[str, list[AdjectiveForm]] = {}
    for form in sentence.forms:
        by_spelling.setdefault(spelling_key(form.text), []).append(form)
    wrong = [readings[0] for readings in by_spelling.values()
             if not same_spelling(readings[0].text, answer.text)
             and not any(is_allowed(form.reading, noun) for form in readings for noun in nouns)]
    ordered = stable_order(wrong, lambda form: form.text, salt=sentence.word + answer.text)
    ordered.sort(key=lambda form: _closeness(form.reading, answer.reading))
    differences = {form.text: _closeness(form.reading, answer.reading) for form in ordered}
    varied = first_distinct(ordered, OPTION_COUNT - 1,
                            lambda form, taken: differences[form.text] not in {differences[other.text] for other in taken})
    rest = [form for form in ordered if form not in varied]
    return [*varied, *rest][:OPTION_COUNT - 1]


def is_allowed(adjective: AdjectiveReading, noun: NounReading) -> bool:
    """The adjective may stand after the noun: it agrees by the rule, or in a way good Arabic also allows."""
    if is_attribute(adjective, noun):
        return True
    same_case_and_state = (adjective.cell.case, adjective.cell.state) == (noun.cell.case, noun.cell.state)
    if not same_case_and_state or noun.cell.number != PLURAL:
        return False
    if not noun.is_human:
        return adjective.cell.number == PLURAL                                  # مَعْدُودَاتٍ، طِبَاقًا
    return (adjective.gender, adjective.cell.number) == (FEMININE, SINGULAR)    # a broken plural of people


def _closeness(adjective: AdjectiveReading, answer: AdjectiveReading) -> int:
    """Which one thing the distractor changes: 0 its gender or number, 1 its case, 2 its definiteness, 3 more."""
    same_case = adjective.cell.case == answer.cell.case
    same_state = adjective.cell.state == answer.cell.state
    same_kind = (adjective.gender, adjective.cell.number) == (answer.gender, answer.cell.number)
    if same_case and same_state:
        return 0
    if same_kind and same_state:
        return 1
    if same_kind and same_case:
        return 2
    return 3


def _rule(noun: NounReading) -> str:
    if noun.cell.number == DUAL:
        return DUAL_RULE
    if noun.cell.number == PLURAL:
        return PEOPLE_RULE if noun.is_human else THINGS_RULE
    return MASCULINE_RULE if noun.gender == MASCULINE else FEMININE_RULE
