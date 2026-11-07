"""Write the two gallery pages of the public site (part of `fil pages`).

    <language>/animations/index.html       every verb animation, every site language
    <language>/noun-pictures/index.html    every noun picture, every site language

Each is in the sitemap only in the languages its captions are written in (fil.pages.gallery_render).
The noun pictures themselves are published by fil.stages.noun_pages, beside the noun pages.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from fil.languages import LANGUAGES
from fil.pages import gallery_render
from fil.pages.gallery_render import Gallery, GalleryItem
from fil.pages.indexing import SOURCE_LANGUAGE


@dataclass(frozen=True)
class GalleryContent:
    gallery: Gallery
    items: tuple[GalleryItem, ...]
    practice: Mapping[str, str] = field(default_factory=dict)   # language → the page of the gallery's exercise

    def practice_in(self, language: str) -> str | None:
        """The exercise page for a reader of `language`: in it where the exercises are written in it, else in English."""
        return self.practice.get(language) or self.practice.get(SOURCE_LANGUAGE)


def write(pages: Path, galleries: Sequence[GalleryContent], texts: dict[str, dict]) -> list[Path]:
    """Every gallery in every language; the pages written. A gallery with nothing to show is a page that still says so."""
    written = []
    for content in galleries:
        for language in LANGUAGES:
            target = pages / content.gallery.path_in(language.code) / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(gallery_render.gallery_page(content.gallery, content.items, language, texts[language.code],
                                                          practice_path=content.practice_in(language.code)),
                              encoding="utf-8")
            written.append(target)
    return written


def page_paths(galleries: Sequence[GalleryContent]) -> list[str]:
    return [path for content in galleries for path in gallery_render.page_paths(content.gallery, content.items)]
