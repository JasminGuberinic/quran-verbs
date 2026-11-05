"""Which category each noun lemma belongs to, and whether a picture can show it.

Every lemma gets one category from a fixed list (docs/NOUNS-PLAN.md, "Categories and
pictures"); a learner browses nouns by it. `is_picturable` marks the concrete things a
small flat icon can show — fruit, animals, body parts, sky, objects — and never people,
prophets, angels or anything sacred: the content policy is decided here, once, so no
picture can be attached to a lemma that is not marked picturable.

Pure: parsing and validation only; the file is read at the edge.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

# The fixed list, in browsing order, with its Bosnian name.
CATEGORIES: Mapping[str, str] = {
    "fruit_vegetables": "voće i povrće",
    "food_drink": "hrana i piće",
    "animals": "životinje",
    "body_parts": "dijelovi tijela",
    "nature_sky": "priroda i nebo",
    "water_sea": "voda i more",
    "house_objects": "kuća i predmeti",
    "clothing": "odjeća",
    "people_family": "ljudi i porodica",
    "time": "vrijeme",
    "places": "mjesta",
    "numbers_quantities": "brojevi i količine",
    "faith_hereafter": "vjera i ahiret",
    "qualities_feelings": "osobine i osjećanja",
    "abstract": "apstraktno",
}

# Categories whose members are never pictured, whatever an entry says. People and time may be
# (owner, 2026-11-05: "narod", "ljudi", "dan", "rob" are not abstract) — people only as faceless
# figures or by an object (a slave by shackles), never a face, never a prophet.
NEVER_PICTURED = frozenset({"faith_hereafter", "qualities_feelings", "abstract", "numbers_quantities"})

LemmaKey = tuple[str, str]   # (lemma, root): three lemmas share their spelling across roots


@dataclass(frozen=True)
class NounCategory:
    """One lemma's category, its English gloss, and whether a picture may show it."""

    lemma: str
    root: str
    gloss_en: str
    category: str
    is_picturable: bool

    @property
    def key(self) -> LemmaKey:
        return self.lemma, self.root


class NounCategoryFormatError(ValueError):
    """A category entry that is malformed, unknown, duplicated or against the content policy."""


def parse_categories(raw: Sequence[Mapping]) -> dict[LemmaKey, NounCategory]:
    """`[{"lemma", "root", "gloss_en", "category", "picturable"}, ...]` → by (lemma, root).

    Fails fast on a missing field, an unknown category, a duplicate lemma, or a picturable
    entry in a category that is never pictured.
    """
    entries: dict[LemmaKey, NounCategory] = {}
    for item in raw:
        entry = _entry(item)
        if entry.key in entries:
            raise NounCategoryFormatError(f"{entry.lemma} ({entry.root}): listed twice")
        entries[entry.key] = entry
    return entries


def picturable(entries: Iterable[NounCategory]) -> list[NounCategory]:
    return [entry for entry in entries if entry.is_picturable]


def as_raw(entries: Iterable[NounCategory]) -> list[dict]:
    """The file form of `entries` — the inverse of `parse_categories`."""
    return [{"lemma": entry.lemma, "root": entry.root, "gloss_en": entry.gloss_en, "category": entry.category,
             "picturable": entry.is_picturable} for entry in entries]


def _entry(item: Mapping) -> NounCategory:
    missing = {"lemma", "root", "gloss_en", "category", "picturable"} - set(item)
    if missing:
        raise NounCategoryFormatError(f"{item.get('lemma', item)!r}: missing {sorted(missing)}")
    entry = NounCategory(lemma=item["lemma"], root=item["root"], gloss_en=item["gloss_en"],
                         category=item["category"], is_picturable=item["picturable"])
    if entry.category not in CATEGORIES:
        raise NounCategoryFormatError(f"{entry.lemma}: unknown category {entry.category!r}")
    if not isinstance(entry.is_picturable, bool):
        raise NounCategoryFormatError(f"{entry.lemma}: picturable must be true or false")
    if entry.is_picturable and entry.category in NEVER_PICTURED:
        raise NounCategoryFormatError(f"{entry.lemma}: {entry.category} is never pictured")
    if not entry.lemma or not entry.gloss_en.strip():
        raise NounCategoryFormatError(f"{entry.lemma!r}: empty lemma or gloss")
    return entry
