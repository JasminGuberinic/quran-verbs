"""Write the particle pages of the public site (part of `fil pages`), and the pronoun pages alike.

    bs/cestica/index.html, en/particle/index.html     the particles, most frequent first
    bs/cestica/<slug>/, en/particle/<slug>/           one particle: what it does, its uses, their ayat
    bs/zamjenica/, en/pronoun/  (and <slug>/)         the pronouns, built the same way (PRONOUNS)

Bosnian and English only for now (docs/PARTICLES-PLAN.md): both are indexed and in the sitemap.
The list sits in the section's folder itself, as the nouns' and adjectives' lists do.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from pathlib import Path

from fil.languages import LANGUAGES, Language
from fil.pages import particle_render
from fil.pages.particle_render import PARTICLES, WordSection


def write(pages: Path, cards: Sequence[dict], texts: dict[str, dict], published: Collection[str],
          section: WordSection = PARTICLES) -> list[Path]:
    """Every page of the section and its list; the pages written."""
    if not cards:
        return []
    written = []
    for language in _languages(section):
        text = texts[language.code]
        written.append(_write(pages, section.index_path(language.code),
                              particle_render.particle_index(cards, language, text, published=published,
                                                             section=section)))
        written += [_write(pages, section.path(language.code, card["slug"]),
                           particle_render.particle_page(card, language, text, published=published, section=section))
                    for card in cards]
    return written


def app_paths(section: WordSection = PARTICLES) -> dict[str, str]:
    """Where the app's link to the section leads, per language (hidden in the others)."""
    return {code: section.index_path(code) for code in section.languages}


def page_paths(cards: Sequence[dict], section: WordSection = PARTICLES) -> list[str]:
    if not cards:
        return []
    return [path for code in section.languages
            for path in (section.index_path(code), *(section.path(code, card["slug"]) for card in cards))]


def _languages(section: WordSection) -> list[Language]:
    return [language for language in LANGUAGES if language.code in section.languages]


def _write(pages: Path, path: str, html: str) -> Path:
    target = pages / path / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")
    return target
