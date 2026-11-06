"""Write the particle pages of the public site (part of `fil pages`).

    bs/cestica/index.html, en/particle/index.html     the particles, most frequent first
    bs/cestica/<slug>/, en/particle/<slug>/           one particle: what it does, its uses, their ayat

Bosnian and English only for now (docs/PARTICLES-PLAN.md): both are indexed and in the sitemap.
The list sits in the particle folder itself, as the nouns' and adjectives' lists do.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from pathlib import Path

from fil.languages import LANGUAGES, Language
from fil.pages import particle_render, seo


def write(pages: Path, cards: Sequence[dict], texts: dict[str, dict], published: Collection[str]) -> list[Path]:
    """Every particle page and the list of particles; the pages written."""
    if not cards:
        return []
    written = []
    for language in _languages():
        text = texts[language.code]
        written.append(_write(pages, seo.particle_index_path(language.code),
                              particle_render.particle_index(cards, language, text, published=published)))
        written += [_write(pages, seo.particle_path(language.code, card["slug"]),
                           particle_render.particle_page(card, language, text, published=published))
                    for card in cards]
    return written


def app_paths() -> dict[str, str]:
    """Where the app's "Particles" link leads, per language (hidden in the others)."""
    return {code: seo.particle_index_path(code) for code in particle_render.PARTICLE_LANGUAGES}


def page_paths(cards: Sequence[dict]) -> list[str]:
    if not cards:
        return []
    return [path for code in particle_render.PARTICLE_LANGUAGES
            for path in (seo.particle_index_path(code), *(seo.particle_path(code, card["slug"]) for card in cards))]


def _languages() -> list[Language]:
    return [language for language in LANGUAGES if language.code in particle_render.PARTICLE_LANGUAGES]


def _write(pages: Path, path: str, html: str) -> Path:
    target = pages / path / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")
    return target
