"""The edge of the noun pictures: emoji files on disk, the data files, the shipped SVGs.

The emoji sets themselves are not in the repository: they are downloaded once (README of
each set) and given by directory — only the recoloured pictures we chose are shipped,
under assets/nouns/. Each set names its files its own way, which is all this adapter knows.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from fil.nouns.categories import LemmaKey, NounCategory, parse_categories
from fil.nouns.palette import SITE_PALETTE, recolour
from fil.nouns.picture_gate import minified, picture_problems
from fil.nouns.pictures import OPENMOJI, TWEMOJI, NounPicture, PictureSource, parse_manifest
from fil.resources import NOUN_CATEGORIES_JSON, NOUN_PICTURES_DIR, NOUN_PICTURES_JSON

_VARIATION_SELECTOR = "-FE0F"


class EmojiNotFound(LookupError):
    """The chosen emoji is missing from the downloaded set."""


@dataclass(frozen=True)
class EmojiDirectory:
    """One downloaded emoji set: OpenMoji names files 1F42A.svg, Twemoji 1f42a.svg (no FE0F)."""

    source: PictureSource
    directory: Path

    def svg(self, codepoint: str) -> str:
        for name in self._file_names(codepoint):
            path = self.directory / name
            if path.is_file():
                return path.read_text(encoding="utf-8")
        raise EmojiNotFound(f"{self.source.title} has no {codepoint} in {self.directory}")

    def _file_names(self, codepoint: str) -> list[str]:
        bare = codepoint.replace(_VARIATION_SELECTOR, "")
        if self.source == TWEMOJI:
            return [f"{bare.lower()}.svg", f"{codepoint.lower()}.svg"]
        return [f"{codepoint}.svg", f"{bare}.svg"]


def emoji_directories(openmoji: Path, twemoji: Path) -> dict[str, EmojiDirectory]:
    return {OPENMOJI.name: EmojiDirectory(OPENMOJI, openmoji), TWEMOJI.name: EmojiDirectory(TWEMOJI, twemoji)}


def shipped_svg(directory: EmojiDirectory, codepoint: str) -> str:
    """The emoji as we ship it: recoloured into the site palette and minified."""
    return minified(recolour(directory.svg(codepoint), SITE_PALETTE))


def load_categories(path: Path = NOUN_CATEGORIES_JSON) -> dict[LemmaKey, NounCategory]:
    return parse_categories(json.loads(path.read_text(encoding="utf-8")))


def load_pictures(path: Path = NOUN_PICTURES_JSON,
                  categories: dict[LemmaKey, NounCategory] | None = None) -> list[NounPicture]:
    return parse_manifest(json.loads(path.read_text(encoding="utf-8")), categories or load_categories())


def write_pictures(pictures: list[NounPicture], directories: dict[str, EmojiDirectory],
                   out_dir: Path = NOUN_PICTURES_DIR) -> list[str]:
    """Write every chosen picture to `out_dir`; the problems of those that fail the gate (not written)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    problems: list[str] = []
    for picture in pictures:
        if picture.source is None:
            continue
        svg = shipped_svg(directories[picture.source.name], picture.codepoint)
        found = picture_problems(svg, SITE_PALETTE)
        if found:
            problems += [f"{picture.slug}: {problem}" for problem in found]
            continue
        (out_dir / picture.file_name).write_text(svg, encoding="utf-8")
    return problems
