"""A noun in English, by rule: "the earth", "in his hand", "of their hands", "two gardens".

English shows no case, so a phrase is the noun's number and state plus the words around
it: the article (definite "the", indefinite "a"/"an" for a countable singular, nothing for a
mass noun or a plural), a possessive pronoun in the article's place, the preposition, "of"
for a genitive no preposition governs, "of" after a noun possessed by the word after it.
"""

from __future__ import annotations

from dataclasses import dataclass

PREPOSITIONS = {"fi": "in", "ala": "on", "bi": "with", "min": "from", "ila": "to", "li": "for", "ka": "like"}
POSSESSIVES = {
    "1S": "my", "1P": "our",
    "2MS": "your", "2FS": "your", "2MP": "your", "2FP": "your", "2D": "your",
    # A third person singular is as often a thing ("its fruit") as a person.
    "3MS": "his/its", "3FS": "her/its", "3MP": "their", "3FP": "their", "3D": "their", "3MD": "their", "3FD": "their",
}
_VOWEL_LETTERS = "aeiou"


@dataclass(frozen=True)
class EnglishNoun:
    singular: str
    plural: str
    is_countable: bool = True      # "a book"; a mass noun ("water", "truth") takes no "a"


@dataclass(frozen=True)
class EnglishPhrase:
    number: str = "S"                 # S, D, P (the corpus's letters)
    is_definite: bool = False
    is_construct: bool = False        # possessed by the word after it: "the way of"
    preposition: str | None = None    # fil.nouns.bosnian.ARABIC_PREPOSITIONS name
    is_genitive: bool = False         # a genitive no preposition governs: "of …"
    possessor: str | None = None
    conjunction: str | None = None    # "and", "so"
    oath: bool = False                # "by the sun"


def phrase(noun: EnglishNoun, wanted: EnglishPhrase) -> str:
    words = [*_leading(wanted), *_determiner(noun, wanted), _noun(noun, wanted.number)]
    if wanted.is_construct and wanted.possessor is None:
        words.append("of")
    return " ".join(word for word in words if word)


def _leading(wanted: EnglishPhrase) -> list[str]:
    words = [wanted.conjunction or ""]
    if wanted.oath:
        return [*words, "by"]
    if wanted.preposition:
        return [*words, PREPOSITIONS[wanted.preposition]]
    return [*words, "of" if wanted.is_genitive else ""]


def _determiner(noun: EnglishNoun, wanted: EnglishPhrase) -> list[str]:
    if wanted.possessor:
        return [POSSESSIVES[wanted.possessor], "two" if wanted.number == "D" else ""]
    is_definite = wanted.is_definite or wanted.is_construct
    if wanted.number == "D":
        return ["the" if is_definite else "", "two"]
    if is_definite:
        return ["the"]
    if wanted.number == "S" and noun.is_countable:
        return ["an" if noun.singular[:1].lower() in _VOWEL_LETTERS else "a"]
    return []


def _noun(noun: EnglishNoun, number: str) -> str:
    return noun.singular if number == "S" else noun.plural
