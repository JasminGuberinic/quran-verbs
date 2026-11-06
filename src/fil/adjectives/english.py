"""An adjective in English, by rule: "a big house", "the big house", "two big houses",
"the house is big", "the house is bigger than the tree".

English adjectives do not agree, so a phrase is the noun's article and number around the
adjective. Pure.
"""

from __future__ import annotations

from fil.nouns.english import EnglishNoun
from fil.nouns.model import DUAL, PLURAL, SINGULAR

_VOWEL_LETTERS = "aeiou"


def attribute(adjective: str, noun: EnglishNoun, number: str, is_definite: bool) -> str:
    """"a big house" / "the big house" / "big houses" / "the two big houses" / "another day"."""
    words = [*_determiner(adjective, noun, number, is_definite), adjective, _noun(noun, number)]
    return " ".join(word for word in words if word).replace("an other ", "another ")


def predicate(adjective: str, noun: EnglishNoun, number: str) -> str:
    """"The house is big." — the subject is definite, as in Arabic (الْبَيْتُ كَبِيرٌ)."""
    subject = attribute("", noun, number, is_definite=True).strip()
    return f"{_sentence_start(subject)} {_be(number)} {adjective}."


def comparison(comparative: str, subject: EnglishNoun, other: EnglishNoun) -> str:
    """"The house is bigger than the tree.\""""
    return f"The {subject.singular} is {comparative} than the {other.singular}."


def phrase(adjective: str, is_definite: bool, conjunction: str | None = None) -> str:
    """A Quranic form without its noun: "and the great", "great"."""
    return " ".join(word for word in (conjunction, "the" if is_definite else "", adjective) if word)


def _determiner(adjective: str, noun: EnglishNoun, number: str, is_definite: bool) -> list[str]:
    if number == DUAL:
        return ["the" if is_definite else "", "two"]
    if is_definite:
        return ["the"]
    if number == SINGULAR and noun.is_countable:
        first = (adjective or noun.singular)[:1].lower()
        return ["an" if first in _VOWEL_LETTERS else "a"]
    return []


def _noun(noun: EnglishNoun, number: str) -> str:
    return noun.singular if number == SINGULAR else noun.plural


def _be(number: str) -> str:
    return "are" if number in (DUAL, PLURAL) else "is"


def _sentence_start(text: str) -> str:
    return text[:1].upper() + text[1:]
