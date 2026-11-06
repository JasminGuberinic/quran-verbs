"""How words look to a learner choosing between them: the same spelling, an overlapping meaning,
one style of writing, and an order that is stable from build to build.

Pure.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Callable, Iterable, Sequence
from typing import TypeVar

from fil.exercises.model import Bilingual
from fil.nouns.spelling import imlai, spelling_key, with_voweled_shadda

Item = TypeVar("Item")

# Words that carry no meaning of their own in a gloss ("to say", "bojati se", "the people").
# site/practice.js reads meanings the same way.
_STOPWORDS = frozenset({"to", "the", "a", "an", "of", "for", "oneself", "se", "i", "je", "u", "na", "od", "za", "and"})
_WORD_BREAK = re.compile(r"[\s,;()/.!?–-]+")
_GLOSS_NOISE = re.compile(r"[!?.,;:]")

# A letter followed straight by a long ā, with no vowel written on it (CAMeL's الرَّحِيمانِ):
# the fatḥa is written, as in every other form a learner compares it with (الرَّحِيمَانِ).
_ARABIC_LETTER = "[ب-ي]"
# Never after the wāw of a verb's plural (قَالُوا), whose alif is silent.
_BARE_BEFORE_ALEF = re.compile(f"(?<={_ARABIC_LETTER})(?<!ُو)(?=ا)")
_FATHA = "َ"


def same_spelling(first: str, second: str) -> bool:
    """Two Arabic forms a reader sees as one word (Uthmani or standard, a fatḥa before alif or none).

    Broad on purpose (it folds hamza seats and a silent final alif too): two options it calls one
    word are never offered together. Whether one spelling *is* two cells is `is_read_alike`'s."""
    return spelling_key(first) == spelling_key(second)


# Uthmani pause and silence marks, the madda sign and tatweel; a vowel on a connecting alif.
# site/practice.js `spellingKey` folds exactly these (a test holds the two equal).
_SILENT_MARKS = re.compile("[\u06dc\u06df-\u06ea\u06e8-\u06ed\u0653\u0640]")
_CONNECTING_ALIF_VOWEL = re.compile("(^|\\s)\u0627[\u064e\u064f\u0650]")


def reading_key(form: str) -> str:
    """A voweled form as a reader of it sees it: equal keys, one spelling with all its readings
    (تَقُولُ: "you say" and "she says"). The app's rule (practice.js `spellingKey`), word for word."""
    word = _SILENT_MARKS.sub("", unicodedata.normalize("NFD", form)).replace("\u0671", "\u0627")
    return unicodedata.normalize("NFC", _CONNECTING_ALIF_VOWEL.sub("\\1\u0627", word))


def is_read_alike(first: str, second: str) -> bool:
    """One spelling: whatever one of the two forms may mean, the other may too (practice.js `readingsOf`)."""
    return reading_key(first) == reading_key(second)


def meaning_words(meaning: str) -> frozenset[str]:
    """The content words of a gloss, lower-cased."""
    return frozenset(word for word in _WORD_BREAK.split(meaning.lower()) if word and word not in _STOPWORDS)


def meanings_overlap(first: Bilingual, second: Bilingual) -> bool:
    """Two meanings share a content word in either language ("srce" and "srce, duša"): offering
    both would leave the learner two right answers."""
    return bool(meaning_words(first.bs) & meaning_words(second.bs) or meaning_words(first.en) & meaning_words(second.en))


def same_gloss(first: Bilingual, second: Bilingual) -> bool:
    """One meaning in either language, punctuation and case aside ("you said" for قُلْتَ and قُلْتِ)."""
    return _folded(first.bs) == _folded(second.bs) or _folded(first.en) == _folded(second.en)


def _folded(gloss: str) -> str:
    return " ".join(_GLOSS_NOISE.sub(" ", gloss.casefold()).split())


def in_one_style(form: str) -> str:
    """A form written the way every other option is: standard spelling (ٱلْأَرْضِ → الْأَرْضِ), the
    vowel of a doubled letter and of a letter before a long ā written. Only folds that keep the
    word what it is — a form the folds would change is returned as it is."""
    standard = imlai(with_voweled_shadda(form))
    voweled = unicodedata.normalize("NFC", _BARE_BEFORE_ALEF.sub(_FATHA, standard))
    return voweled if same_spelling(voweled, form) else standard


def stable_order(items: Iterable[Item], key_of: Callable[[Item], str], salt: str) -> list[Item]:
    """The items in an order that looks random but is the same in every build (and differs by `salt`)."""
    return sorted(items, key=lambda item: hashlib.sha1(f"{salt}|{key_of(item)}".encode()).hexdigest())


def first_distinct(candidates: Sequence[Item], count: int, is_distinct: Callable[[Item, Sequence[Item]], bool]) -> list[Item]:
    """Up to `count` candidates, in order, each distinct from those already taken."""
    taken: list[Item] = []
    for candidate in candidates:
        if len(taken) == count:
            break
        if is_distinct(candidate, taken):
            taken.append(candidate)
    return taken
