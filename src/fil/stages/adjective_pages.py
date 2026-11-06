"""Write the adjective pages of the public site (part of `fil pages`).

    bs/pridjev/index.html, en/adjective/index.html    the studied adjectives, by frequency, with categories
    bs/pridjev/<slug>/, en/adjective/<slug>/          one adjective: agreement table and examples, sentences, the Quran
    ayat/adjective-<slug>[.<lang>].json               every ayah of an adjective, fetched on request

Bosnian and English only for now (docs/NOUNS-PLAN.md): both are indexed and in the sitemap.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from fil.languages import LANGUAGES, Language
from fil.pages import adjective_render, seo
from fil.stages.adjective_site import AdjectiveContent
from fil.stages.noun_pages import write_ayat


def write(pages: Path, adjectives: AdjectiveContent, nouns: Sequence[dict], texts: dict[str, dict],
          credit_for: Callable[[Sequence[dict]], str] = lambda _cards: "") -> list[Path]:
    """Every adjective page and list and the adjectives' ayat files; the pages written. `credit_for`
    gives the picture credit owed for the noun cards a page links (fil.stages.noun_pages.credits)."""
    if not adjectives.cards:
        return []
    write_ayat(pages, adjectives.ayat_lists)
    written = []
    for language in _languages():
        text = texts[language.code]
        written.append(_write(pages, seo.adjective_index_path(language.code),
                              adjective_render.adjective_index(adjectives.cards, language, text)))
        for card in adjectives.cards:
            nouns_of_root = adjective_render.of_root(card, nouns)
            html = adjective_render.adjective_page(card, language, text, related=adjective_render.of_root(card, adjectives.cards),
                                                   nouns_of_root=nouns_of_root, picture_credit=credit_for(nouns_of_root))
            written.append(_write(pages, seo.adjective_path(language.code, card["slug"]), html))
    return written


def app_paths() -> dict[str, str]:
    """Where the app's "Adjectives" link leads, per language (hidden in the others)."""
    return {code: seo.adjective_index_path(code) for code in adjective_render.ADJECTIVE_LANGUAGES}


def page_paths(adjectives: Sequence[dict]) -> list[str]:
    if not adjectives:
        return []
    return [path for code in adjective_render.ADJECTIVE_LANGUAGES
            for path in (seo.adjective_index_path(code), *(seo.adjective_path(code, card["slug"]) for card in adjectives))]


def _languages() -> list[Language]:
    return [language for language in LANGUAGES if language.code in adjective_render.ADJECTIVE_LANGUAGES]


def _write(pages: Path, path: str, html: str) -> Path:
    target = pages / path / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")
    return target
