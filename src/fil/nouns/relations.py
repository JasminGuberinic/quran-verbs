"""Nouns that are not one thing each: collectives, their single ones, and male/female pairs.

Arabic has nouns a plain "singular / dual / plural" table teaches wrongly:

  - a **collective** names a group and has no singular of its own (اسم جمع): إِبِل "camels"
    — one camel is جَمَل (a male) or نَاقَة (a she-camel); قَوْم "a people", نَاس "people".
    Some collectives have a **singulative**, the same word with -ة for one of them (اسم جنس
    جمعي): نَخْل "date palms" → نَخْلَة "a date palm", شَجَر → شَجَرَة, طَيْر → طَائِر. Neither kind
    has a dual or a plural of its own meaning, and what agrees with it (verb, adjective,
    pronoun) follows usage, not its form: الْإِبِلُ تَأْكُلُ — feminine.
  - a **singulative** is the "one" of such a collective: شَجَرَة of شَجَر, بَقَرَة of بَقَر.
  - a **pair** is a noun whose male and female are different words: بَقَرَة "cow" / ثَوْر "bull",
    عَبْد "male slave" / أَمَة "female slave".

What a noun is, and which words it relates to, is reviewed linguistic data
(data/noun_relations.json), never inferred at render time; `likely_collective` only
flags lemmas a batch must look at. A reviewed noun that is none of these is `ordinary`.

Pure: entries in, validated relations out.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from fil.nouns import gate
from fil.nouns.model import FEMININE, INDEFINITE, MASCULINE, NOMINATIVE, PLURAL, SINGULAR, Cell, NounLemma
from fil.nouns.spelling import skeleton

# ------------------------------------------------------------------ what a noun is

COLLECTIVE = "collective"       # إِبِل, قَوْم, نَخْل: a group, no singular of its own
SINGULATIVE = "singulative"     # شَجَرَة: one of the collective شَجَر
PAIR = "pair"                   # بَقَرَة / ثَوْر, عَبْد / أَمَة: male and female are different words
ORDINARY = "ordinary"           # flagged by `likely_collective`, reviewed, and none of the above
KINDS = (COLLECTIVE, SINGULATIVE, PAIR, ORDINARY)

# How what refers to a collective agrees with it, as the Quran and classical usage have it.
AGREES_FEMININE = "F"                  # الْإِبِلُ تَأْكُلُ
AGREES_MASCULINE = "M"
AGREES_EITHER = "MF"                   # قَالَ قَوْمُهُ / كَذَّبَتْ قَوْمُ نُوحٍ; أَعْجَازُ نَخْلٍ مُنْقَعِرٍ / نَخْلٍ خَاوِيَةٍ
AGREES_MASCULINE_PLURAL = "MP"         # يَا أَيُّهَا النَّاسُ اعْبُدُوا
AGREEMENTS = (AGREES_FEMININE, AGREES_MASCULINE, AGREES_EITHER, AGREES_MASCULINE_PLURAL)

# ------------------------------------------------------------------ how a related word relates

ONE = "one"                     # one of the collective: نَخْلَة of نَخْل, إِنْسَان of نَاس
OF_COLLECTIVE = "collective"    # the collective a singulative is one of: شَجَر of شَجَرَة
MALE = "male"                   # جَمَل of إِبِل, ثَوْر of بَقَرَة
FEMALE = "female"               # نَاقَة of إِبِل, أَمَة of عَبْد
ROLES = (ONE, MALE, FEMALE, OF_COLLECTIVE)
_ROLES_OF_KIND = {COLLECTIVE: {ONE, MALE, FEMALE}, SINGULATIVE: {OF_COLLECTIVE, MALE, FEMALE},
                  PAIR: {MALE, FEMALE}, ORDINARY: set()}

_GENDERS = (MASCULINE, FEMININE)
_ARABIC_LETTERS = re.compile(r"^[ء-يً-ْٰ]+$")
_LATIN = re.compile(r"^[a-zA-ZčćžšđČĆŽŠĐ ,'()/-]+$")
_TA_MARBUTA = "ة"


class InvalidNounRelation(ValueError):
    """A relation entry that must not reach a learner; the message names every problem."""


@dataclass(frozen=True)
class RelatedNoun:
    """A word a noun's card shows beside it: one of it, its male or female, its collective."""

    role: str                   # one of ROLES
    arabic: str                 # the indefinite nominative with full harakat: نَاقَةٌ
    gender: str                 # M | F
    en: str
    bs: str
    lemma: str | None = None    # the corpus lemma|root when the Quran has the word: "ناقَة|نوق"


@dataclass(frozen=True)
class NounRelation:
    """A studied noun's kind, how what refers to it agrees, and the words it relates to."""

    key: str                    # the studied noun, lemma|root
    kind: str                   # one of KINDS
    why: str                    # the reviewer's reason, with the evidence
    agreement: str | None = None            # a collective's agreement (AGREEMENTS)
    related: tuple[RelatedNoun, ...] = ()

    @property
    def is_collective(self) -> bool:
        return self.kind == COLLECTIVE

    @property
    def has_singulative(self) -> bool:
        return any(word.role == ONE for word in self.related)


def parse_relations(entries: Mapping[str, Mapping]) -> dict[str, NounRelation]:
    """The stored entries (key → entry), validated; InvalidNounRelation names every problem."""
    problems = [problem for key, entry in entries.items() for problem in _problems(key, entry)]
    if problems:
        raise InvalidNounRelation("; ".join(problems))
    return {key: _relation(key, entry) for key, entry in entries.items()}


def _relation(key: str, entry: Mapping) -> NounRelation:
    related = tuple(RelatedNoun(role=word["role"], arabic=word["ar"], gender=word["gender"], en=word["en"],
                                bs=word["bs"], lemma=word.get("lemma")) for word in entry.get("related", ()))
    return NounRelation(key=key, kind=entry["kind"], why=entry["why"], agreement=entry.get("agreement"), related=related)


def _problems(key: str, entry: Mapping) -> list[str]:
    if not isinstance(entry, Mapping):
        return [f"{key}: an entry is an object"]
    kind = entry.get("kind")
    if kind not in KINDS:
        return [f"{key}: kind must be one of {', '.join(KINDS)}, not {kind!r}"]
    found = []
    if not str(entry.get("why", "")).strip():
        found.append(f"{key}: says no why")
    agreement = entry.get("agreement")
    if kind == COLLECTIVE and agreement not in AGREEMENTS:
        found.append(f"{key}: a collective needs its agreement, one of {', '.join(AGREEMENTS)}")
    if kind != COLLECTIVE and agreement is not None:
        found.append(f"{key}: only a collective has an agreement of its own")
    related = entry.get("related", ())
    found += [problem for word in related for problem in _word_problems(key, kind, word)]
    found += _shape_problems(key, kind, related)
    return found


def _shape_problems(key: str, kind: str, related: Sequence[Mapping]) -> list[str]:
    roles = [word.get("role") for word in related]
    found = [f"{key}: {role} twice" for role in set(roles) if roles.count(role) > 1]
    if kind == SINGULATIVE and OF_COLLECTIVE not in roles:
        found.append(f"{key}: a singulative names its collective")
    if kind == PAIR and not {MALE, FEMALE} & set(roles):
        found.append(f"{key}: a pair names its male or female")
    if kind == ORDINARY and related:
        found.append(f"{key}: an ordinary noun relates to nothing here")
    return found


def _word_problems(key: str, kind: str, word: Mapping) -> list[str]:
    where = f"{key} → {word.get('ar', '?')}"
    role, arabic = word.get("role"), str(word.get("ar", ""))
    found = []
    if role not in _ROLES_OF_KIND[kind]:
        found.append(f"{where}: a {kind} has no {role!r}")
    if word.get("gender") not in _GENDERS:
        found.append(f"{where}: gender must be M or F")
    if role == FEMALE and word.get("gender") != FEMININE or role == MALE and word.get("gender") != MASCULINE:
        found.append(f"{where}: a {role} with gender {word.get('gender')!r}")
    if role == ONE and kind == COLLECTIVE and _is_singulative(arabic) and word.get("gender") != FEMININE:
        found.append(f"{where}: a singulative in -ة is feminine")
    for language in ("en", "bs"):
        if not _LATIN.match(str(word.get(language, ""))):
            found.append(f"{where}: {language} must be plain text")
    found += _arabic_problems(where, arabic, word.get("lemma"))
    return found


def _arabic_problems(where: str, arabic: str, lemma: str | None) -> list[str]:
    """The citation form: an indefinite nominative, fully vowelled, that passes the noun gate;
    when the Quran has the word, the same letters as its lemma."""
    if not _ARABIC_LETTERS.match(unicodedata.normalize("NFC", arabic)):
        return [f"{where}: Arabic letters and harakat only"]
    found = [f"{where}: {problem}" for problem in gate.problems(arabic, Cell(SINGULAR, INDEFINITE, NOMINATIVE), arabic)]
    if lemma is not None and "|" not in lemma:
        found.append(f"{where}: lemma is written lemma|root")
    if lemma and skeleton(arabic) != skeleton(lemma.split("|")[0]):
        found.append(f"{where}: not the letters of its lemma {lemma}")
    return found


def _is_singulative(arabic: str) -> bool:
    return skeleton(arabic).endswith(_TA_MARBUTA)


# ------------------------------------------------------------------ the batch check

# Collectives a lemma's tags do not reveal: no singulative in the Quran, a singular tag.
KNOWN_COLLECTIVES = frozenset({
    "إِبِل", "قَوْم", "ناس", "رَهْط", "نَفَر", "غَنَم", "خَيْل", "طَيْر", "نَخْل", "شَجَر", "بَقَر", "نَحْل", "نَمْل",
    "جَراد", "قُمَّل", "ثَمَر", "حَبّ", "زَرْع", "عِنَب", "تِين", "زَيْتُون", "رُمّان", "سِدْر", "أَثْل", "طَلْح", "جِنّ",
    "إِنس", "بَشَر", "سَحاب", "مَوْج", "رُوم", "نِساء", "ضَأْن", "مَعْز", "حَصَب", "حِجارَة", "قِرَدَة", "قَصَب",
})


def likely_collective(lemma: NounLemma, catalogue: Iterable[NounLemma]) -> str | None:
    """Why `lemma` may be a collective, a singulative or one of a pair a batch must review —
    or None. A guess for a reviewer, never a decision: the reviewed answer goes into
    data/noun_relations.json (`ordinary` when it is none of them)."""
    if lemma.lemma in KNOWN_COLLECTIVES:
        return "known collective"
    if lemma.numbers == (PLURAL,) and not lemma.plurals[1:] and _plural_is_lemma(lemma):
        return "only ever plural, with no plural pattern of its own (اسم جمع?)"
    siblings = {(other.lemma, other.root) for other in catalogue}
    letters = skeleton(lemma.lemma)
    if letters.endswith(_TA_MARBUTA) and any(skeleton(other) == letters[:-1] for other, root in siblings
                                             if root == lemma.root):
        return f"a word of the same root without -ة ({letters[:-1]}): its collective, or its male?"
    if any(skeleton(other) == letters + _TA_MARBUTA for other, root in siblings if root == lemma.root):
        return f"a word of the same root in -ة ({letters}{_TA_MARBUTA}): its singulative, or its female?"
    return None


def _plural_is_lemma(lemma: NounLemma) -> bool:
    return any(skeleton(plural.text).removeprefix("ال") == skeleton(lemma.lemma) for plural in lemma.plurals)
