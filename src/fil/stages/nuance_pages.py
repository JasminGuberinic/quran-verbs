"""Write the nuance pages of the public site (part of `fil pages`).

    bs/nijanse/index.html, en/nuances/index.html    the groups of near-synonyms
    bs/nijanse/<slug>/, en/nuances/<slug>/          one group: what they share, each word, its ayat

Bosnian and English only for now (docs/NUANCES-PLAN.md): both are indexed and in the sitemap.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from pathlib import Path

from fil.languages import LANGUAGES, Language
from fil.pages import nuance_render, seo


def write(pages: Path, cards: Sequence[dict], texts: dict[str, dict], published: Collection[str]) -> list[Path]:
    """Every group page and the list of groups; the pages written."""
    if not cards:
        return []
    written = []
    for language in _languages():
        text = texts[language.code]
        written.append(_write(pages, seo.nuance_index_path(language.code),
                              nuance_render.nuance_index(cards, language, text, published=published)))
        written += [_write(pages, seo.nuance_path(language.code, card["slug"]),
                           nuance_render.nuance_page(card, language, text, published=published))
                    for card in cards]
    return written


def app_paths() -> dict[str, str]:
    """Where the app's "Nuances" link leads, per language (hidden in the others)."""
    return {code: seo.nuance_index_path(code) for code in nuance_render.NUANCE_LANGUAGES}


def page_paths(cards: Sequence[dict]) -> list[str]:
    if not cards:
        return []
    return [path for code in nuance_render.NUANCE_LANGUAGES
            for path in (seo.nuance_index_path(code), *(seo.nuance_path(code, card["slug"]) for card in cards))]


def _languages() -> list[Language]:
    return [language for language in LANGUAGES if language.code in nuance_render.NUANCE_LANGUAGES]


def _write(pages: Path, path: str, html: str) -> Path:
    target = pages / path / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")
    return target
