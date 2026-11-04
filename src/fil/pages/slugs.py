"""The ASCII name of a verb's page: قالَ → qala, so /en/qala/ reads well in a link.

A slug must never change once published (a link someone shared, a search result), so it
is decided over the whole Quranic verb catalogue — fixed by the corpus — not over the
verbs studied so far: adding a verb never renames another. Where two verbs read the same
in ASCII, the more frequent keeps the plain name and the next gets -2, -3, …
"""

from __future__ import annotations

import re
from collections.abc import Iterable

_CONSONANTS = {
    "ب": "b", "ت": "t", "ث": "th", "ج": "j", "ح": "h", "خ": "kh", "د": "d", "ذ": "dh",
    "ر": "r", "ز": "z", "س": "s", "ش": "sh", "ص": "s", "ض": "d", "ط": "t", "ظ": "z",
    "غ": "gh", "ف": "f", "ق": "q", "ك": "k", "ل": "l", "م": "m", "ن": "n", "ه": "h",
    "و": "w", "ي": "y",
    # ʿayn and hamza have no plain-ASCII letter; a link reads better without them
    "ع": "", "ء": "", "أ": "", "إ": "", "ؤ": "", "ئ": "",
}
_VOWELS = {"َ": "a", "ِ": "i", "ُ": "u", "ً": "an"}
_SHADDA = "ّ"
# A long vowel after its own short vowel adds nothing to the ASCII reading (قَالَ → qala).
_LENGTHENS = {"ا": "a", "ى": "a", "و": "u", "ي": "i"}
_SILENT = {"ْ", "۟", "ۢ", "ۥ"}   # sukun and small Quranic marks
_FALLBACK = "verb"


def slug_of(lemma: str) -> str:
    """A lowercase ASCII reading of a vocalised Arabic verb."""
    reading: list[str] = []
    last_vowel = ""
    for position, letter in enumerate(_shadda_first(lemma)):
        if letter in _SILENT:
            continue
        if letter in _VOWELS:
            last_vowel = _VOWELS[letter]
            reading.append(last_vowel)
            continue
        if letter == _SHADDA:
            reading.append(_last_consonant(reading))
            continue
        reading.append(_letter(letter, last_vowel, is_first=position == 0))
        last_vowel = ""
    slug = re.sub(r"[^a-z0-9]+", "-", "".join(reading)).strip("-")
    return slug or _FALLBACK


def _letter(letter: str, last_vowel: str, is_first: bool) -> str:
    if letter == "آ":
        return "a"
    if letter == "ا" and is_first:
        return "i"     # the connecting alif of اتَّقَى, اتَّبَعَ: ittaqa
    if letter in _LENGTHENS:
        return "" if last_vowel == _LENGTHENS[letter] else _long_or_consonant(letter)
    return _CONSONANTS.get(letter, "")


def _long_or_consonant(letter: str) -> str:
    return _CONSONANTS.get(letter, "a")


def _shadda_first(lemma: str) -> str:
    """Shadda and its vowel are written in either order; read the doubling first."""
    return re.sub(r"([\u064b-\u0650]+)\u0651", "\u0651\\1", lemma)


def _last_consonant(reading: list[str]) -> str:
    """Shadda doubles the consonant before it."""
    return reading[-1] if reading else ""


def assign_slugs(lemmas_by_frequency: Iterable[str]) -> list[str]:
    """One unique slug per lemma, in the given order (most frequent first)."""
    taken: set[str] = set()
    slugs = []
    for lemma in lemmas_by_frequency:
        slug = _free_variant(slug_of(lemma), taken)
        taken.add(slug)
        slugs.append(slug)
    return slugs


def _free_variant(base: str, taken: set[str]) -> str:
    if base not in taken:
        return base
    suffix = 2
    while f"{base}-{suffix}" in taken:
        suffix += 1
    return f"{base}-{suffix}"
