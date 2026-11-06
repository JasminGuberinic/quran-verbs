"""Write the root pages of the public site (part of `fil pages`).

    bs/korijen/index.html, en/root/index.html    the roots, alphabetical, with a letter index and a search box
    bs/korijen/<slug>/, en/root/<slug>/          one root: its meaning, its core idea, every word it gives the Quran

Bosnian and English only for now (docs/ROOTS-PLAN.md): both are indexed and in the sitemap.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from pathlib import Path

from fil.exercises.model import ADJECTIVE_WORD, NOUN_WORD, PARTICLE_WORD, VERB_WORD, word_id
from fil.languages import LANGUAGES, Language
from fil.pages import exercise_render, root_render, seo
from fil.roots.model import ADJECTIVE_PAGE, NOUN_PAGE, PARTICLE_PAGE, VERB_PAGE, RootPage

# The exercise family of each kind of page a word links to (fil.exercises.model.word_id).
_FAMILY_OF_PAGE = {VERB_PAGE: VERB_WORD, NOUN_PAGE: NOUN_WORD, ADJECTIVE_PAGE: ADJECTIVE_WORD, PARTICLE_PAGE: PARTICLE_WORD}


def write(pages: Path, roots: Sequence[RootPage], texts: dict[str, dict], published: Collection[str],
          nuances: Sequence[dict] = (), kinds_of_word: Mapping[str, Sequence[str]] | None = None) -> list[Path]:
    """Every root page and the list of roots; the pages written. `nuances` are the group cards a root's
    words stand in; `kinds_of_word` the exercise kinds that ask about each word (fil.stages.exercises)."""
    if not roots:
        return []
    titles = {card["slug"]: card["title"] for card in nuances}
    written = []
    for language in _languages():
        text = texts[language.code]
        written.append(_write(pages, seo.root_index_path(language.code),
                              root_render.root_index(roots, language, text, published=published)))
        for page in roots:
            path = seo.root_path(language.code, page.slug)
            practice = exercise_render.words_practice_link(exercise_words(page), kinds_of_word or {}, language, text,
                                                           seo.to_root(path))
            written.append(_write(pages, path, root_render.root_page(page, language, text, published=published,
                                                                     nuance_titles=titles, practice=practice)))
    return written


def exercise_words(page: RootPage) -> list[str]:
    """The exercise ids of a root's studied words ("verb:qala", "noun:qawl"), most frequent first."""
    return list(dict.fromkeys(word_id(_FAMILY_OF_PAGE[found.kind], found.slug)
                              for word in page.studied for found in word.pages))


def slugs_by_root(roots: Sequence[RootPage]) -> dict[str, str]:
    """Where each root's page is, by its letters: what the verb, noun and adjective cards link."""
    return {page.root: page.slug for page in roots}


def app_paths() -> dict[str, str]:
    """Where the app's "Roots" link leads, per language (hidden in the others)."""
    return {code: seo.root_index_path(code) for code in root_render.ROOT_LANGUAGES}


def page_paths(roots: Sequence[RootPage]) -> list[str]:
    if not roots:
        return []
    return [path for code in root_render.ROOT_LANGUAGES
            for path in (seo.root_index_path(code), *(seo.root_path(code, page.slug) for page in roots))]


def _languages() -> list[Language]:
    return [language for language in LANGUAGES if language.code in root_render.ROOT_LANGUAGES]


def _write(pages: Path, path: str, html: str) -> Path:
    target = pages / path / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")
    return target
