"""Write the About pages of the public site (part of `fil pages`).

    bs/about/index.html, en/about/index.html, …    every site language, each indexed and in the sitemap
"""

from __future__ import annotations

from collections.abc import Collection
from pathlib import Path

from fil.languages import LANGUAGES
from fil.pages import about_render, seo


def write(pages: Path, texts: dict[str, dict], published: Collection[str] = frozenset()) -> list[Path]:
    """One About page per language; the pages written. `published` names the sections the menus lead to."""
    written = []
    for language in LANGUAGES:
        target = pages / seo.about_path(language.code) / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(about_render.about_page(language, texts, published), encoding="utf-8")
        written.append(target)
    return written


def page_paths() -> list[str]:
    return [seo.about_path(language.code) for language in LANGUAGES]
