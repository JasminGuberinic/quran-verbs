"""The gate a generated noun form must pass before a learner may see it.

A generator is trusted for nothing the Quran can check, and the ending of a declined noun
is fully determined by its cell: the article by the state, the last vowel by the case,
the shape of the ending by the number and the kind of plural. A form whose ending says
another cell than the one it was generated for is refused — and so is the one ending
Arabic never writes, a case vowel on the yāʾ of a defective noun (الأَيْدِيُ), and a letter
written with two vowels (حَيََّاتٌ: a fatḥa left over when an ending was joined on).

Pure: a form and a cell in, the list of problems out (empty = it passes).
"""

from __future__ import annotations

import unicodedata

from fil.nouns.catalogue import plural_kind
from fil.nouns.model import (ACCUSATIVE, DEFINITE, DUAL, GENITIVE, NOMINATIVE, PLURAL, SOUND_FEMININE,
                             SOUND_MASCULINE, Cell)
from fil.nouns.spelling import spelling_key

_DAMMA, _FATHA, _KASRA = chr(0x064F), chr(0x064E), chr(0x0650)
_DAMMATAN, _FATHATAN, _KASRATAN = chr(0x064C), chr(0x064B), chr(0x064D)
_NUNATION = {_DAMMATAN, _FATHATAN, _KASRATAN}
_CASE_VOWELS = {NOMINATIVE: {_DAMMA, _DAMMATAN}, ACCUSATIVE: {_FATHA, _FATHATAN}, GENITIVE: {_KASRA, _KASRATAN}}
# A diptote has no nunation and takes fatḥa in the genitive (أَشْيَاءَ); a sound feminine
# plural takes kasra in the accusative (ثَمَرَاتٍ).
_SUN_LETTERS = set("تثدذرزسشصضطظلن")
_SHADDA = chr(0x0651)
_ALL_VOWELS = _CASE_VOWELS[NOMINATIVE] | _CASE_VOWELS[ACCUSATIVE] | _CASE_VOWELS[GENITIVE]
_ALL_MARKS = {chr(code) for code in range(0x064B, 0x0653)}
_VOWELS_AND_SUKUN = _ALL_VOWELS | {chr(0x0652)}
_DIPTOTE_VOWELS = {NOMINATIVE: {_DAMMA}, ACCUSATIVE: {_FATHA}, GENITIVE: {_FATHA}}
_FEMININE_PLURAL_VOWELS = {NOMINATIVE: {_DAMMA, _DAMMATAN}, ACCUSATIVE: {_KASRA, _KASRATAN},
                           GENITIVE: {_KASRA, _KASRATAN}}
_SOUND_ENDINGS = {(PLURAL, NOMINATIVE): "ون" + _FATHA, (PLURAL, ACCUSATIVE): "ين" + _FATHA,
                  (PLURAL, GENITIVE): "ين" + _FATHA, (DUAL, NOMINATIVE): "ان" + _KASRA,
                  (DUAL, ACCUSATIVE): "ين" + _KASRA, (DUAL, GENITIVE): "ين" + _KASRA}


def problems(form: str, cell: Cell, lemma: str) -> tuple[str, ...]:
    """Every way `form` fails to be the `cell` of `lemma`; empty when it passes."""
    text = spelling_key(form)
    found = [_state_problem(form, cell), _two_vowels_problem(form), _defective_problem(text), _long_alif_problem(text),
             _ending_problem(text, form, cell, lemma)]
    return tuple(problem for problem in found if problem)


def _state_problem(form: str, cell: Cell) -> str | None:
    is_definite = has_article(form)
    if cell.state == DEFINITE and not is_definite:
        return "definite without the article"
    if cell.state != DEFINITE and is_definite:
        return "indefinite with the article"
    if cell.state == DEFINITE and _NUNATION & set(unicodedata.normalize("NFD", form)):
        return "definite with nunation"
    if cell.state == DEFINITE and not _is_assimilated(form):
        return "sun letter after the article not doubled"
    return None


def _is_assimilated(form: str) -> bool:
    """After the article a sun letter is written doubled: الشَّجَرَة, never الشَجَرَة."""
    text = unicodedata.normalize("NFD", form)
    letters = [index for index, char in enumerate(text) if not unicodedata.combining(char)]
    if len(letters) < 3 or text[letters[2]] not in _SUN_LETTERS:
        return True
    marks = text[letters[2] + 1:letters[3] if len(letters) > 3 else len(text)]
    return _SHADDA in marks


def has_article(form: str) -> bool:
    """A bare or waṣl alif, then lām — not the hamza of أَلِيم or إِلٰه, which folding would hide."""
    text = unicodedata.normalize("NFC", form)
    letters = [char for char in text if not unicodedata.combining(char)]
    return letters[:2] in (["ا", "ل"], ["ٱ", "ل"])


def _two_vowels_problem(form: str) -> str | None:
    """A letter carries at most one vowel (or sukūn) — beside it only a shadda."""
    marks = _letter_marks(unicodedata.normalize("NFD", form))
    is_doubled = any(sum(mark in _VOWELS_AND_SUKUN for mark in letter) > 1 for letter in marks)
    return "two vowels on one letter" if is_doubled else None


def _letter_marks(text: str) -> list[str]:
    """The marks written on each letter, in order."""
    found: list[str] = []
    for char in text:
        if unicodedata.combining(char) and found:
            found[-1] += char
        elif not unicodedata.combining(char):
            found.append("")
    return found


def _defective_problem(text: str) -> str | None:
    """A defective noun's final yāʾ is silent in the nominative and genitive (الْأَيْدِي)."""
    if text.endswith((_KASRA + "ي" + _DAMMA, _KASRA + "ي" + _KASRA)):
        return "case vowel on a defective yāʾ"
    return None


def _long_alif_problem(text: str) -> str | None:
    """A final long alif carries no case vowel (الْعَصَا, never الْعَصاُ); only nunation's
    fatḥatān may be written on its seat alif (كِتَاباً)."""
    marks = _trailing_marks(text)
    if text[:len(text) - len(marks)].endswith("ا") and set(marks) & (_ALL_VOWELS - {_FATHATAN}):
        return "case vowel on a final alif"
    return None


def _ending_problem(text: str, form: str, cell: Cell, lemma: str) -> str | None:
    """`text` is the folded spelling the endings are read from; `form` as written, whose
    letters (hamza seats and all) say what kind of plural it is."""
    if cell.number == DUAL or (cell.number == PLURAL and plural_kind(lemma, form) == SOUND_MASCULINE):
        expected = _SOUND_ENDINGS[(cell.number, cell.case)]
        return None if text.endswith(expected) else f"{cell.case} {cell.number} must end in -{expected}"
    if _is_defective(text, cell) or _is_indeclinable(text):
        return None
    vowel = _final_vowel(text)
    allowed = _allowed_vowels(form, cell, lemma)
    return None if vowel in allowed else f"{cell.case} ending expected, found {_name(vowel)}"


def _allowed_vowels(form: str, cell: Cell, lemma: str) -> set[str]:
    if cell.number == PLURAL and plural_kind(lemma, form) == SOUND_FEMININE:
        return _FEMININE_PLURAL_VOWELS[cell.case]
    if cell.state == DEFINITE:
        return _CASE_VOWELS[cell.case] - _NUNATION
    return _CASE_VOWELS[cell.case] | _DIPTOTE_VOWELS[cell.case]


def _is_defective(text: str, cell: Cell) -> bool:
    """أَيْدٍ / الْأَيْدِي in the nominative and genitive — the accusative is regular (أَيْدِيًا)."""
    if cell.case == ACCUSATIVE:
        return False
    return text.endswith(_KASRATAN) or (text.endswith("ي") and text[-2:-1] == _KASRA)


def _final_vowel(text: str) -> str | None:
    """The vowel on the last letter; nunation written before its seat alif (كِتَابًا, حَقًّا) counts."""
    body = text[:-1] if text.endswith("ا") and _FATHATAN in _trailing_marks(text[:-1]) else text
    return next((mark for mark in _trailing_marks(body) if mark in _ALL_VOWELS), None)


def _trailing_marks(text: str) -> str:
    return text[len(text.rstrip("".join(_ALL_MARKS))):]


def _is_indeclinable(text: str) -> bool:
    """A noun ending in a long alif (الدُّنْيَا, هُدًى) shows no case at all."""
    if text.endswith("ا"):
        return _FATHATAN not in _trailing_marks(text[:-1])
    return text.endswith("ي") and bool({_FATHA, _FATHATAN} & set(_trailing_marks(text[:-1])))


def _name(vowel: str | None) -> str:
    return unicodedata.name(vowel).removeprefix("ARABIC ").lower() if vowel else "no vowel"
