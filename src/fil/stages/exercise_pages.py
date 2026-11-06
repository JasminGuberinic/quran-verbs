"""Write the exercise pages of the public site (part of `fil pages`).

    bs/vjezbe/index.html, en/exercises/index.html      the hub: every kind, and a mixed practice
    bs/vjezbe/<kind>/, en/exercises/<kind>/             one kind (koji-padez / which-case, …)
    exercises/<kind>-<n>.json                           the questions (fil.stages.exercises)

Bosnian and English only for now (docs/EXERCISES-PLAN.md): both are indexed and in the sitemap.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from pathlib import Path

from fil.languages import LANGUAGES, Language
from fil.pages import exercise_render, seo
from fil.stages import exercises


def write(pages: Path, sets: exercises.ExerciseSets, texts: Mapping[str, dict], published: Collection[str]) -> list[Path]:
    """The questions' shards, the hub and a page per kind; the pages written."""
    if not sets.kinds():
        return []
    counts = sets.counts()
    shards = exercises.write(pages, sets)
    written = []
    for language in _languages():
        written.append(_write(pages, seo.exercise_index_path(language.code),
                              exercise_render.hub_page(language, texts, counts, shards, published=published)))
        written += [_write(pages, exercise_render.kind_path(language.code, kind, texts),
                           exercise_render.kind_page(kind, language, texts, counts, shards, published=published))
                    for kind in sets.kinds()]
    return written


def app_paths() -> dict[str, str]:
    """Where the app's "Exercises" link leads, per language (hidden in the others)."""
    return {code: seo.exercise_index_path(code) for code in exercise_render.EXERCISE_LANGUAGES}


def page_paths(sets: exercises.ExerciseSets, texts: Mapping[str, dict]) -> list[str]:
    if not sets.kinds():
        return []
    return [path for code in exercise_render.EXERCISE_LANGUAGES
            for path in (seo.exercise_index_path(code),
                         *(exercise_render.kind_path(code, kind, texts) for kind in sets.kinds()))]


def _languages() -> list[Language]:
    return [language for language in LANGUAGES if language.code in exercise_render.EXERCISE_LANGUAGES]


def _write(pages: Path, path: str, html: str) -> Path:
    target = pages / path / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")
    return target
