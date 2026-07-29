"""Vocalization correctness helpers for Arabic verb forms.

For a Quran-learning app, a form whose final letter has no ḥarakah is
incompletely voweled and unacceptable (the generator sometimes emits a bare
final consonant, e.g. "كَتَبْتُم" instead of "كَتَبْتُمْ"). These pure functions
enforce full vocalization: `with_pausal_sukun` supplies the missing pausal sukūn
on a bare final consonant, and `has_vocalized_ending` is the invariant we assert
on every form we ship.
"""

from __future__ import annotations

SUKUN = "ْ"

# Combining marks that count as vocalizing the letter they sit on
# (ḥarakāt, tanwīn, shadda, sukūn, superscript alef).
_DIACRITICS = {chr(cp) for cp in range(0x064B, 0x0653)} | {"ٰ"}

# Base letters that legitimately end a word WITHOUT a ḥarakah because they are
# themselves the long vowel / alif (alif, alif maqṣūra, alif madda, wāw, yāʾ).
_LONG_VOWEL_LETTERS = {"ا", "ى", "آ", "و", "ي"}

# The Arabic base-letter range (consonants + hamza carriers), excluding the
# combining marks that begin at U+064B.
_BASE_LETTER_RANGE = range(0x0621, 0x064B)


def _is_bare_final_consonant(letter: str) -> bool:
    """True if `letter` is a consonant that, at word end, still needs a sukūn."""
    return ord(letter) in _BASE_LETTER_RANGE and letter not in _LONG_VOWEL_LETTERS


def with_pausal_sukun(form: str) -> str:
    """Add the pausal sukūn to a form ending in a bare consonant; else unchanged.

    In pausal (citation) form any final consonant takes a sukūn, so this is a
    safe, meaning-preserving completion — it never touches a form that already
    ends in a ḥarakah or a long vowel.
    """
    if not form:
        return form
    if _is_bare_final_consonant(form[-1]):
        return form + SUKUN
    return form


def has_any_diacritic(text: str) -> bool:
    """True if the text carries at least one tashkīl mark (used to reject an
    unvocalized authored form)."""
    return any(ch in _DIACRITICS for ch in text)


def has_vocalized_ending(form: str) -> bool:
    """True if the form's final character is a diacritic or a long-vowel letter.

    This is the invariant every shipped form must satisfy — it fails exactly the
    bare-final-consonant case.
    """
    if not form:
        return False
    return form[-1] in _DIACRITICS or form[-1] in _LONG_VOWEL_LETTERS
