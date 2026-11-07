"""Which emoji pictures which noun: the manifest of noun pictures.

A picturable noun (fil.nouns.categories) is shown by one open-licence emoji, recoloured
into our greens (fil.nouns.palette), or by our own drawing where no emoji fits. For each noun a reviewer compared the same emoji from
two sets and chose the more recognisable — or neither, when neither shows the noun
clearly; such a noun gets no picture rather than a misleading one. The manifest records
the choice, the set it came from and the original codepoint, so every shipped file can be
traced back to its licensed source and rebuilt.

Pure: parsing and validation only; the files are read and written at the edge.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from fil.nouns.categories import LemmaKey, NounCategory


@dataclass(frozen=True)
class PictureSource:
    """An emoji set we may redistribute, recoloured, under its licence."""

    name: str
    title: str
    url: str
    licence: str
    licence_url: str


OPENMOJI = PictureSource(name="openmoji", title="OpenMoji", url="https://openmoji.org",
                         licence="CC BY-SA 4.0", licence_url="https://creativecommons.org/licenses/by-sa/4.0/")
TWEMOJI = PictureSource(name="twemoji", title="Twemoji", url="https://github.com/jdecked/twemoji",
                        licence="CC BY 4.0", licence_url="https://creativecommons.org/licenses/by/4.0/")
# Drawn by hand in our palette where no emoji shows the noun correctly (fig, river, sky, faceless
# people, and symbols such as a figure carrying a load for a burden). Ours, so they owe no licence and
# are never regenerated; the credit only says which pictures are ours (fil.pages.picture_credits).
OWN_DRAWING = PictureSource(name="fil", title="Fiʿl", url="https://jasminguberinic.github.io/quran-verbs/",
                            licence="own drawing", licence_url="")
CREDITED: tuple[PictureSource, ...] = (OPENMOJI, TWEMOJI)
SOURCES: Mapping[str, PictureSource] = {source.name: source for source in (*CREDITED, OWN_DRAWING)}


@dataclass(frozen=True)
class NounPicture:
    """A picturable noun and the emoji chosen for it; `source` is None when none fits."""

    lemma: str
    root: str
    slug: str
    bosnian: str
    codepoint: str               # e.g. "1F42A"; empty when no emoji was found at all
    source: PictureSource | None

    @property
    def key(self) -> LemmaKey:
        return self.lemma, self.root

    @property
    def has_picture(self) -> bool:
        return self.source is not None

    @property
    def file_name(self) -> str:
        return f"{self.slug}.svg"


class PictureManifestError(ValueError):
    """A manifest entry that is malformed, duplicated, or pictures a noun it may not."""


def parse_manifest(raw: Sequence[Mapping], categories: Mapping[LemmaKey, NounCategory]) -> list[NounPicture]:
    """`[{"lemma", "root", "slug", "bs", "codepoint", "source": "openmoji"|"twemoji"|null}]` → pictures.

    Fails fast on a missing field, an unknown source, a duplicate noun or slug, or a noun
    the categories do not mark picturable — the content policy is decided there.
    """
    pictures = [_picture(item) for item in raw]
    _require_unique((picture.key for picture in pictures), "noun")
    _require_unique((picture.slug for picture in pictures), "slug")
    for picture in pictures:
        category = categories.get(picture.key)
        if category is None or not category.is_picturable:
            raise PictureManifestError(f"{picture.lemma} ({picture.root}): not a picturable noun")
    return pictures


def as_raw(pictures: Iterable[NounPicture]) -> list[dict]:
    """The file form of `pictures` — the inverse of `parse_manifest`."""
    return [{"lemma": picture.lemma, "root": picture.root, "slug": picture.slug, "bs": picture.bosnian,
             "codepoint": picture.codepoint, "source": picture.source.name if picture.source else None}
            for picture in pictures]


def shown(pictures: Iterable[NounPicture]) -> list[NounPicture]:
    return [picture for picture in pictures if picture.has_picture]


def sources_used(pictures: Iterable[NounPicture]) -> list[PictureSource]:
    """The licensed sets the given pictures come from, in a fixed order (for the credit line)."""
    names = {picture.source.name for picture in pictures if picture.source}
    return [source for source in CREDITED if source.name in names]


def _picture(item: Mapping) -> NounPicture:
    missing = {"lemma", "root", "slug", "bs", "codepoint", "source"} - set(item)
    if missing:
        raise PictureManifestError(f"{item.get('lemma', item)!r}: missing {sorted(missing)}")
    source_name = item["source"]
    if source_name is not None and source_name not in SOURCES:
        raise PictureManifestError(f"{item['lemma']}: unknown source {source_name!r}")
    if not item["slug"] or not item["slug"].replace("-", "").isalnum() or not item["slug"].isascii():
        raise PictureManifestError(f"{item['lemma']}: slug {item['slug']!r} is not lowercase ASCII")
    if source_name not in (None, OWN_DRAWING.name) and not re.fullmatch(r"[0-9A-F]{4,5}(?:-[0-9A-F]{4,5})*", item["codepoint"]):
        raise PictureManifestError(f"{item['lemma']}: a picture needs its emoji codepoint, got {item['codepoint']!r}")
    return NounPicture(lemma=item["lemma"], root=item["root"], slug=item["slug"], bosnian=item["bs"],
                       codepoint=item["codepoint"], source=SOURCES[source_name] if source_name else None)


def _require_unique(values: Iterable, what: str) -> None:
    seen: set = set()
    for value in values:
        if value in seen:
            raise PictureManifestError(f"{what} {value!r} listed twice")
        seen.add(value)
