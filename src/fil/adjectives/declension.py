"""An adjective's regular cells declined by rule: the second generator, after CAMeL.

CAMeL's MSA lexicon lacks many adjectives' plurals (كَبِير has neither كِبَار nor كَبِيرَات)
and a few adjectives altogether (حَمِيد is only a name there), yet their declension is the
most regular part of Arabic morphology:

  - a singular or a broken plural: a triptote takes -un/-an/-in (كِبَارٌ كِبَارًا كِبَارٍ), a
    diptote — the فُعَلَاء, أَفْعِلَاء and فَعْلَاء patterns, ending in -āʾ — -u/-a/-a without
    nunation (عُظَمَاءُ عُظَمَاءَ), and both -u/-a/-i with the article (الْعُظَمَاءِ);
  - the dual: -āni / -ayni (كَبِيرَانِ, كَبِيرَتَيْنِ — tāʾ marbūṭa opens to tāʾ);
  - the sound plurals: -ūna / -īna (كَبِيرُونَ), -ātun / -ātin (كَبِيرَاتٌ).

The rule declines only what it can say for sure: a stem ending in a long vowel or a hamza
(أَعْمَى, بَرِيء — whose seat may change before an ending) is refused (CannotDecline) and its
cells are left to CAMeL or stay empty. A broken plural is written once by the drafter. Every
form still passes the noun gate (fil.nouns.gate) before it ships.

Pure.
"""

from __future__ import annotations

import unicodedata

from fil.nouns.model import ACCUSATIVE, CASES, DEFINITE, DUAL, GENITIVE, INDEFINITE, NOMINATIVE, SINGULAR
from fil.nouns.spelling import skeleton, with_voweled_shadda

_DAMMA, _FATHA, _KASRA = "ُ", "َ", "ِ"
_DAMMATAN, _FATHATAN, _KASRATAN = "ٌ", "ً", "ٍ"
_SHADDA, _SUKUN = "ّ", "ْ"
_ALL_MARKS = "".join(chr(code) for code in range(0x064B, 0x0653))
_SUN_LETTERS = set("تثدذرزسشصضطظلن")
_TRIPTOTE = {(INDEFINITE, NOMINATIVE): _DAMMATAN, (INDEFINITE, ACCUSATIVE): _FATHATAN,
             (INDEFINITE, GENITIVE): _KASRATAN}
_DIPTOTE = {(INDEFINITE, NOMINATIVE): _DAMMA, (INDEFINITE, ACCUSATIVE): _FATHA, (INDEFINITE, GENITIVE): _FATHA}
_DEFINITE = {(DEFINITE, NOMINATIVE): _DAMMA, (DEFINITE, ACCUSATIVE): _FATHA, (DEFINITE, GENITIVE): _KASRA}


_HAMZAS = ("ء", "أ", "ؤ", "ئ", "إ")
SOUND_MASCULINE_ENDINGS = {NOMINATIVE: _DAMMA + "ون" + _FATHA, ACCUSATIVE: _KASRA + "ين" + _FATHA,
                           GENITIVE: _KASRA + "ين" + _FATHA}
_DUAL_OBLIQUE = _FATHA + "ي" + _SUKUN + "ن" + _KASRA    # كَبِيرَيْنِ
_DUAL_ENDINGS = {NOMINATIVE: _FATHA + "ان" + _KASRA, ACCUSATIVE: _DUAL_OBLIQUE, GENITIVE: _DUAL_OBLIQUE}
_FEMININE_PLURAL_ENDINGS = {(INDEFINITE, NOMINATIVE): _DAMMATAN, (INDEFINITE, ACCUSATIVE): _KASRATAN,
                            (INDEFINITE, GENITIVE): _KASRATAN, (DEFINITE, NOMINATIVE): _DAMMA,
                            (DEFINITE, ACCUSATIVE): _KASRA, (DEFINITE, GENITIVE): _KASRA}

Forms = dict[tuple[str, str], str]   # (state, case) → the form


class CannotDecline(ValueError):
    """The stem is not one this rule declines (it ends in a long vowel or a hamza: مَوْتَى, بَرِيء)."""


def declined_number(singular: str, number: str, plural: str | None = None, is_diptote_singular: bool = False) -> Forms:
    """The six cells of one number of a side whose singular is `singular` (كَبِير or كَبِيرَة).
    `plural` says which plural: a sound one ("sound") or a broken stem (كِبَار); a singular of a
    diptote pattern (أَفْعَل: آخَرُ, أَبْيَضُ) is declined without nunation."""
    if number == SINGULAR:
        return declined(singular, is_diptote_singular)
    if number == DUAL:
        return dual(singular)
    if plural == "sound":
        return sound_plural(singular)
    if plural:
        return declined(plural)
    raise CannotDecline(f"{singular}: no plural to decline")


def _nfc(forms: Forms) -> Forms:
    """One spelling for one form: marks in canonical order (حَيًّا, not حَيًّا with shadda last),
    and a doubled letter with its vowel — a lemma written without the fatḥa before a long ā
    (صابِر) would otherwise give الصّابِرُ, not the Quran's الصَّابِرُ."""
    return {cell: with_voweled_shadda(text) for cell, text in forms.items()}


def dual(singular: str) -> Forms:
    stem = _checked(singular)
    stem = stem[:-1] + "ت" if stem.endswith("ة") else stem
    stem = stem.removesuffix(_FATHA)
    return _nfc({(state, case): (with_article(stem) if state == DEFINITE else stem) + _DUAL_ENDINGS[case]
                 for state in (DEFINITE, INDEFINITE) for case in CASES})


def sound_plural(singular: str) -> Forms:
    """كَبِير → كَبِيرُونَ; كَبِيرَة → كَبِيرَاتٌ."""
    stem = _checked(singular)
    if stem.endswith("ة"):
        base = _without_final_fatha(stem[:-1]) + _FATHA + "ات"
        return _nfc({(state, case): (with_article(base) if state == DEFINITE else base)
                     + _FEMININE_PLURAL_ENDINGS[(state, case)] for state in (DEFINITE, INDEFINITE) for case in CASES})
    return _nfc({(state, case): (with_article(stem) if state == DEFINITE else stem) + SOUND_MASCULINE_ENDINGS[case]
                 for state in (DEFINITE, INDEFINITE) for case in CASES})


def _without_final_fatha(text: str) -> str:
    """The last letter's marks without its fatḥa: in canonical order حَيَّة writes the fatḥa
    before the shadda (يَّ), so a plain removesuffix would leave it and double it (حَيََّات)."""
    letters = text.rstrip(_ALL_MARKS)
    return letters + text[len(letters):].replace(_FATHA, "")


def elative_nominative(elative: str) -> str | None:
    """أَكْبَر → أَكْبَرُ: the comparative is a diptote; one ending in a long vowel (أَدْنَى) shows no case."""
    text = unicodedata.normalize("NFC", elative.strip())
    if text.rstrip("".join(chr(code) for code in range(0x064B, 0x0653))).endswith("ى") or skeleton(text).endswith(("ا", *_HAMZAS)):
        return None
    return unicodedata.normalize("NFC", text + _DAMMA)


def _checked(stem: str) -> str:
    """A doubled wāw or yāʾ is a consonant (حَيّ, عَرَبِيّ, قَوِيّ); a single one a long vowel."""
    text = unicodedata.normalize("NFC", stem.strip())
    letters = skeleton(text)
    is_doubled = text.rstrip(_FATHA + _DAMMA + _KASRA).endswith(_SHADDA)
    if not letters or letters.endswith(("ى", "ا", *_HAMZAS)) or (letters.endswith(("و", "ي")) and not is_doubled):
        raise CannotDecline(f"{stem}: a stem ending in a long vowel or a hamza is declined by hand, not by rule")
    return text


def declined(stem: str, is_diptote_pattern: bool = False) -> Forms:
    """A singular's or broken plural's bare stem → its cells: كِبَار → {(definite, NOM): الْكِبَارُ …}.
    A stem ending in -āʾ is a diptote by its letters; `is_diptote_pattern` says so for the others
    (أَفْعَل), which the letters alone cannot tell from a triptote."""
    is_without_nunation = is_diptote_pattern or is_diptote(stem)
    stem = unicodedata.normalize("NFC", stem.strip()) if is_diptote(stem) else _checked(stem)
    endings = {**(_DIPTOTE if is_without_nunation else _TRIPTOTE), **_DEFINITE}
    return _nfc({(state, case): _form(stem, state, endings[(state, case)])
                 for state in (DEFINITE, INDEFINITE) for case in CASES})


def is_diptote(stem: str) -> bool:
    """فُعَلَاء, أَفْعِلَاء, فَعْلَاء: a word ending in -āʾ takes no nunation."""
    return skeleton(stem).endswith("اء")


def _form(stem: str, state: str, ending: str) -> str:
    if state == DEFINITE:
        return with_article(stem) + ending
    if ending == _FATHATAN and not skeleton(stem).endswith(("ة", "اء")):
        return stem + ending + "ا"     # كِبَارًا: nunation's seat alif
    return stem + ending


def with_article(stem: str) -> str:
    """الْكِبَار, الشِّدَاد: the lām silent before a moon letter, the sun letter doubled."""
    first, rest = stem[0], stem[1:]
    if first in _SUN_LETTERS:
        return "ال" + first + _SHADDA + rest
    return "ال" + _SUKUN + stem
