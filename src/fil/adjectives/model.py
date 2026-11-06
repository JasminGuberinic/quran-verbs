"""What a studied adjective is: its meaning, the nouns its card shows it with, its table.

Pure data. An adjective has a masculine and a feminine side, each a case table like a
noun's (fil.nouns.studied.NounTable): singular, dual, plural × definite, indefinite ×
NOM, ACC, GEN. Only what the Quran says or the gate accepts fills a cell.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from fil.nouns.model import FEMININE, MASCULINE, Cell
from fil.nouns.studied import NounTable, noun_key, split_key

GENDERS = (MASCULINE, FEMININE)

# The masculine plural an adjective takes where the Quran has none: none at all (it does not
# describe people: أَلِيم), the sound plural CAMeL makes (-ūna), or a broken plural written once
# by the drafter (كِبَار) and declined by rule (fil.adjectives.declension).
NO_PLURAL, SOUND_PLURAL = "-", "sound"

CATEGORIES = ("size_quantity", "people_qualities", "condition", "moral", "intensity", "time_distance",
              "knowledge_clarity", "colours", "other")


class InvalidAdjectiveData(ValueError):
    """A stored adjective entry that must not reach a learner; the message names what is wrong."""


@dataclass(frozen=True)
class DescribedNouns:
    """The studied nouns (lemma|root keys) the card's agreement examples describe."""

    masculine: str          # بَيْت → بَيْتٌ كَبِيرٌ, الْبَيْتُ الْكَبِيرُ, الْبَيْتُ كَبِيرٌ
    feminine: str           # شَجَرَة → شَجَرَةٌ كَبِيرَةٌ
    thing_plural: str = ""  # بَيْت → بُيُوتٌ كَبِيرَةٌ (a plural of things takes the feminine singular) —
                            # none for an adjective said of people only (عَلِيم)
    human_plural: str = ""  # رِجَال → رِجَالٌ كِبَارٌ — only when the adjective has a masculine plural

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(key for key in (self.masculine, self.feminine, self.thing_plural, self.human_plural) if key)


@dataclass(frozen=True)
class Elative:
    """The comparative (أَفْعَلُ مِنْ) in the learner's languages: "bigger", "veći"."""

    en: str
    bs: str


@dataclass(frozen=True)
class AdjectiveMeaning:
    lemma: str
    root: str
    en: str                      # "big, large" — the first sense composes the glosses
    bs: str                      # "velik, krupan" — shown
    bs_short: str                # "velik": the short masculine form a Bosnian predicate takes ("grad je velik")
    bs_long: str                 # "veliki": the long masculine nominative every other form is declined from
    feminine: str                # "كَبِيرَة": the feminine singular as the dictionary writes it
    has_feminine_lemma: bool     # the corpus files the feminine as a lemma of its own (كَثِيرَة) and it is this adjective
    pattern: str                 # "فَعِيل"
    category: str
    nouns: DescribedNouns
    masculine_plural: str = NO_PLURAL
    elative: Elative | None = None

    @property
    def key(self) -> str:
        return noun_key(self.lemma, self.root)

    @property
    def en_first(self) -> str:
        return self.en.split(",")[0].strip()


def parse_meaning(key: str, entry: Mapping) -> AdjectiveMeaning:
    lemma, root = split_key(key)
    required = ("en", "bs", "bsShort", "bsLong", "feminine", "pattern", "category", "nouns")
    missing = [field for field in required if not entry.get(field)]
    if not root or missing:
        raise InvalidAdjectiveData(f"{key}: {'no root' if not root else 'missing ' + ', '.join(missing)}")
    if entry["category"] not in CATEGORIES:
        raise InvalidAdjectiveData(f"{key}: category {entry['category']!r} is not one of {', '.join(CATEGORIES)}")
    nouns = entry["nouns"]
    if not all(nouns.get(field) for field in ("masculine", "feminine")):
        raise InvalidAdjectiveData(f"{key}: the agreement examples need a masculine and a feminine noun")
    elative = entry.get("elative")
    return AdjectiveMeaning(
        lemma=lemma, root=root, en=entry["en"], bs=entry["bs"], bs_short=entry["bsShort"], bs_long=entry["bsLong"],
        feminine=entry["feminine"], has_feminine_lemma=bool(entry.get("feminineLemma", False)),
        pattern=entry["pattern"], category=entry["category"],
        nouns=DescribedNouns(nouns["masculine"], nouns["feminine"], nouns.get("thingPlural", ""), nouns.get("humanPlural", "")),
        masculine_plural=entry.get("masculinePlural", NO_PLURAL),
        elative=Elative(elative["en"], elative["bs"]) if elative else None)


def meaning_entry(meaning: AdjectiveMeaning) -> dict:
    nouns = {"masculine": meaning.nouns.masculine, "feminine": meaning.nouns.feminine}
    if meaning.nouns.thing_plural:
        nouns["thingPlural"] = meaning.nouns.thing_plural
    if meaning.nouns.human_plural:
        nouns["humanPlural"] = meaning.nouns.human_plural
    entry = {"en": meaning.en, "bs": meaning.bs, "bsShort": meaning.bs_short, "bsLong": meaning.bs_long,
             "feminine": meaning.feminine, "feminineLemma": meaning.has_feminine_lemma, "pattern": meaning.pattern,
             "category": meaning.category, "nouns": nouns, "masculinePlural": meaning.masculine_plural}
    if meaning.elative:
        entry["elative"] = {"en": meaning.elative.en, "bs": meaning.elative.bs}
    return entry


@dataclass(frozen=True)
class AdjectiveTable:
    """Both genders' case tables; a side the gate leaves empty has no rows."""

    key: str
    masculine: NounTable
    feminine: NounTable
    elative: str | None = None    # the comparative's indefinite nominative (أَكْبَرُ), Quranic or gated

    def side(self, gender: str) -> NounTable:
        return self.masculine if gender == MASCULINE else self.feminine

    def cells(self) -> tuple[tuple[str, Cell, str], ...]:
        """Every filled cell as (gender, cell, text); a second plural's under the plural's cell."""
        return tuple((gender, cell, text) for gender in GENDERS for cell, text in self.side(gender).cells())

    def text(self, gender: str, number: str, state: str, case: str) -> str | None:
        """The main row's cell (never a second plural's)."""
        row = next((row for row in self.side(gender).rows if row.row == number), None)
        return row.text(state, case) if row else None
