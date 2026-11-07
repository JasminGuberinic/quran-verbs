"""Which category each noun lemma belongs to, and whether a picture can show it.

Every lemma gets one category from a fixed list (docs/NOUNS-PLAN.md, "Categories and
pictures"); a learner browses nouns by it. `is_picturable` marks what a small flat icon can
show — fruit, animals, body parts, sky, objects, people as plain faceless silhouettes, and an
abstract noun through a symbol a reader connects with it (scales for justice) — and never God,
a prophet, death or killing: the content policy is decided here, once, so no picture can be
attached to a lemma that is not marked picturable.

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

LemmaKey = tuple[str, str]   # (lemma, root): three lemmas share their spelling across roots

# Categories whose members are never pictured, whatever an entry says. People and time may be
# (owner, 2026-11-05: "narod", "ljudi", "dan", "rob" are not abstract). Owner, 2026-11-06:
# people, heads and faces only as plain silhouettes without facial features (no eyes, mouth or
# expression); a body part that is the noun itself (eye, ear, tongue) is drawn as that part.
NEVER_PICTURED = frozenset({"faith_hereafter"})

# Owner, 2026-11-07: abstract nouns, feelings and quantities may be pictured by a symbol a reader
# connects with the meaning (scales for justice, a broken heart for grief, a figure carrying a load
# for a burden); a noun no symbol shows clearly gets none. A symbol is not a drawing of the thing,
# so a picture question never asks it (fil.exercises.vocabulary).
SYMBOLIC = frozenset({"qualities_feelings", "abstract", "numbers_quantities"})

# The few sacred things the owner allows as plain symbols in our greens despite their category:
# an angel only as wings and light, never a figure or a face (2026-11-06); and (2026-11-07) worship,
# Paradise, the unseen and God's acts only through objects, places and their effects, never a figure
# standing for a person beyond a faceless worshipper — a garden for Paradise, a prostrating
# silhouette for prayer, open palms for supplication, a curtain for the unseen, a compass for the
# qiblah, a charity box for alms, a lit path to a star for guidance; and the Kaaba, which the owner
# allows plainly, for the pilgrimage, the Umrah and their rites. (A mosque, a miḥrāb and statues are
# places and objects, so their categories already allow them.) God, His names and the prophets as
# persons stay banned below.
SYMBOLS_OF_THE_SACRED: frozenset[LemmaKey] = frozenset({
    ("مَلَك", "ملك"), ("جَنَّة", "جنن"), ("صَلاة", "صلو"), ("دُعاء", "دعو"),
    ("غَيْب", "غيب"), ("قِبْلَة", "قبل"), ("صَدَقَة", "صدق"), ("هُدًى", "هدي"),
    ("حَجّ", "حجج"), ("عُمْرَة", "عمر"), ("مَنسَك", "نسك"),
})

# Never pictured, whatever their category or an entry says: God, His Throne, and the prophets;
# and (owner, 2026-11-07) the soul, death, killing and war, which no symbol may show either.
NEVER_PICTURED_LEMMAS: frozenset[LemmaKey] = frozenset({
    ("رَبّ", "ربب"), ("إِلٰه", "أله"), ("عَرْش", "عرش"), ("كُرْسِيّ", "كرس"),
    ("نَبِيّ", "نبأ"), ("نُبُوَّة", "نبأ"), ("رَسُول", "رسل"), ("مُرْسَل", "رسل"),
    ("نَفْس", "نفس"), ("رُوح", "روح"), ("مَوْت", "موت"), ("قَتْل", "قتل"), ("قِتال", "قتل"),
    ("حَرْب", "حرب"), ("قِصاص", "قصص"),
})


def is_never_pictured(category: str, key: LemmaKey) -> bool:
    """The content policy: whether no picture may ever show this lemma."""
    if key in NEVER_PICTURED_LEMMAS:
        return True
    return category in NEVER_PICTURED and key not in SYMBOLS_OF_THE_SACRED


def is_symbolic(category: str | None) -> bool:
    """Whether a picture of a noun of this category can only be a symbol of it, not the thing itself."""
    return category in SYMBOLIC or category in NEVER_PICTURED


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
    entry the content policy never pictures.
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
    if entry.is_picturable and is_never_pictured(entry.category, entry.key):
        raise NounCategoryFormatError(f"{entry.lemma}: the content policy never pictures it ({entry.category})")
    if not entry.lemma or not entry.gloss_en.strip():
        raise NounCategoryFormatError(f"{entry.lemma!r}: empty lemma or gloss")
    return entry
