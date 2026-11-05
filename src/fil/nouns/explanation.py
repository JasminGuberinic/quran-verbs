"""What each case does, shown with the noun itself: the heart of a noun card.

    NOM  the subject                     ٱلْبَيْتُ            kuća (nominativ)
    ACC  the object                      ٱلْبَيْتَ            kuću (akuzativ)
    GEN  after a preposition (two)       فِي ٱلْبَيْتِ        u kući (lokativ)
    GEN  the possessor in an iḍāfa       بَابُ ٱلْبَيْتِ      vrata kuće (genitiv)
    —    a possessive suffix             بَيْتُهُ             njegova kuća

Each example is built from the noun's own case table (fil.nouns.paradigm) and its stored
Bosnian declension; the two prepositions are the ones the Quran uses with this noun most.
The possessive example is the Quran's own word where it has one (a possessed noun with
nothing else attached), composed like any form; otherwise it is made by rule from a
regular nominative (بَيْتٌ → بَيْتُهُ) and marked as ours. Pure.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from fil.nouns import bosnian, english
from fil.nouns.compose import Composed, NounGlossing
from fil.nouns.english import EnglishPhrase
from fil.nouns.model import ACCUSATIVE, DEFINITE, GENITIVE, INDEFINITE, NOMINATIVE, PLURAL, SINGULAR

SUBJECT, OBJECT, AFTER_PREPOSITION, POSSESSOR, POSSESSIVE_SUFFIX = (
    "subject", "object", "afterPreposition", "possessor", "possessiveSuffix")
# How each Arabic preposition is written before a definite noun; بِ joins it.
WRITTEN_PREPOSITIONS = {"fi": "فِي ", "ala": "عَلَى ", "min": "مِنَ ", "ila": "إِلَى ", "bi": "بِ"}
DEFAULT_PREPOSITIONS = ("fi", "min", "ila")
PREPOSITIONS_SHOWN = 2
_DAMMATAN, _DAMMA = "ٌ", "ُ"
_SUFFIX_HIS = "هُ"
_IRREGULAR_BEFORE_SUFFIX = set("ءأإآؤئاىي")   # a hamza or long vowel changes the stem before a suffix


@dataclass(frozen=True)
class Idafa:
    """The word a noun is shown possessing: بَابُ (+ ٱلْبَيْتِ) "the door of" / "vrata"."""

    arabic: str      # nominative, construct: بَابُ
    en: str          # door
    bs: str          # vrata


@dataclass(frozen=True)
class QuranicPossessive:
    arabic: str
    gloss: Composed
    location: tuple[int, int, int]


@dataclass(frozen=True)
class Example:
    role: str
    arabic_case: str         # NOM, ACC, GEN, or "" for the possessive (its case is the noun's own)
    arabic: str
    en: str
    bs: str
    bosnian_case: str        # N, A, L…
    is_quranic: bool = False
    location: tuple[int, int, int] | None = None


def examples(cells: Mapping[tuple[str, str, str], str], noun: NounGlossing, idafa: Idafa | None,
             prepositions: Sequence[str], possessive: QuranicPossessive | None) -> tuple[Example, ...]:
    """The case examples for one noun, from its table `cells` ((number, state, case) → text)."""
    number = SINGULAR if any(key[0] == SINGULAR for key in cells) else PLURAL
    found = [
        _plain(cells, noun, number, NOMINATIVE, SUBJECT),
        _plain(cells, noun, number, ACCUSATIVE, OBJECT),
        *_after_prepositions(cells, noun, number, prepositions),
        _possessor(cells, noun, number, idafa),
        _possessive(cells, noun, number, possessive),
    ]
    return tuple(example for example in found if example is not None)


def chosen_prepositions(by_frequency: Sequence[str]) -> tuple[str, ...]:
    """The prepositions to show, in order: the noun's commonest in the Quran, then فِي and مِنْ."""
    usable = [name for name in by_frequency if name in WRITTEN_PREPOSITIONS]
    return tuple(dict.fromkeys([*usable, *DEFAULT_PREPOSITIONS]))


def _after_prepositions(cells, noun: NounGlossing, number: str, by_frequency: Sequence[str]) -> list[Example]:
    """Two examples, from the first prepositions the noun's Bosnian composes."""
    found = (_after_preposition(cells, noun, number, name) for name in chosen_prepositions(by_frequency))
    return [example for example in found if example is not None][:PREPOSITIONS_SHOWN]


def _definite(cells, number: str, case: str) -> tuple[str, bool] | None:
    """The definite cell, else the indefinite; and whether it is the definite."""
    for state in (DEFINITE, INDEFINITE):
        text = cells.get((number, state, case))
        if text:
            return text, state == DEFINITE
    return None


def _bosnian_number(number: str) -> str:
    return bosnian.PLURAL if number == PLURAL else bosnian.SINGULAR


def _plain(cells, noun: NounGlossing, number: str, case: str, role: str) -> Example | None:
    found = _definite(cells, number, case)
    bosnian_case = bosnian.NOMINATIVE if case == NOMINATIVE else bosnian.ACCUSATIVE
    text = noun.bosnian.cell(_bosnian_number(number), bosnian_case)
    if not found or not text:
        return None
    arabic, is_definite = found
    en = english.phrase(noun.english, EnglishPhrase(number=number, is_definite=is_definite))
    return Example(role, case, arabic, en, text, bosnian_case)


def _after_preposition(cells, noun: NounGlossing, number: str, name: str) -> Example | None:
    found = _definite(cells, number, GENITIVE)
    if not found:
        return None
    arabic, is_definite = found
    wanted = bosnian.Phrase(number=_bosnian_number(number), preposition=name)
    try:
        bs = bosnian.phrase(noun.bosnian, wanted)
    except bosnian.CannotSay:
        return None
    written = WRITTEN_PREPOSITIONS[name] if is_definite or name == "bi" else WRITTEN_PREPOSITIONS[name].replace("مِنَ", "مِنْ")
    en = english.phrase(noun.english, EnglishPhrase(number=number, is_definite=is_definite, preposition=name))
    return Example(AFTER_PREPOSITION, GENITIVE, written + arabic, en, bs, bosnian.case_of(noun.bosnian, wanted))


def _possessor(cells, noun: NounGlossing, number: str, idafa: Idafa | None) -> Example | None:
    found = _definite(cells, number, GENITIVE)
    genitive = noun.bosnian.cell(_bosnian_number(number), bosnian.GENITIVE)
    if idafa is None or not found or not genitive:
        return None
    arabic, is_definite = found
    en = f"the {idafa.en} of " + english.phrase(noun.english, EnglishPhrase(number=number, is_definite=is_definite))
    return Example(POSSESSOR, GENITIVE, f"{idafa.arabic} {arabic}", en, f"{idafa.bs} {genitive}", bosnian.GENITIVE)


def _possessive(cells, noun: NounGlossing, number: str, quranic: QuranicPossessive | None) -> Example | None:
    if quranic is not None:
        return Example(POSSESSIVE_SUFFIX, "", quranic.arabic, quranic.gloss.en, quranic.gloss.bs,
                       quranic.gloss.bosnian_case, is_quranic=True, location=quranic.location)
    arabic = with_his(cells.get((number, INDEFINITE, NOMINATIVE)) or "")
    if not arabic:
        return None
    wanted = bosnian.Phrase(number=_bosnian_number(number), possessor="3MS")
    try:
        bs = bosnian.phrase(noun.bosnian, wanted)
    except bosnian.CannotSay:
        return None
    en = english.phrase(noun.english, EnglishPhrase(number=number, possessor="3MS"))
    return Example(POSSESSIVE_SUFFIX, "", arabic, en, bs, bosnian.NOMINATIVE)


def with_his(nominative: str) -> str | None:
    """بَيْتٌ → بَيْتُهُ, شَجَرَةٌ → شَجَرَتُهُ; None for a stem a suffix would change otherwise
    (a final hamza or long vowel: مَاءٌ → مَاؤُهُ), or a nominative without nunation."""
    if not nominative.endswith(_DAMMATAN):
        return None
    stem = nominative[:-1]
    letters = [char for char in stem if char.isalpha()]
    if not letters or letters[-1] in _IRREGULAR_BEFORE_SUFFIX:
        return None
    if letters[-1] == "ة":
        position = stem.rindex("ة")
        stem = stem[:position] + "ت" + stem[position + 1:]
    return stem + _DAMMA + _SUFFIX_HIS
