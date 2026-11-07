"""Write the exercise pages of the public site (part of `fil pages`).

    bs/vjezbe/index.html, en/exercises/index.html      the hub: every kind, and a mixed practice
    bs/vjezbe/<kind>/, en/exercises/<kind>/             one kind (koji-padez / which-case, …)
    exercises/<kind>-<n>.json                           the questions (fil.stages.exercises)

Bosnian and English only for now (docs/EXERCISES-PLAN.md): both are indexed and in the sitemap.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from pathlib import Path, PurePosixPath

from fil.exercises.model import PICTURE
from fil.languages import LANGUAGES, Language
from fil.nouns.pictures import NounPicture
from fil.pages import exercise_render, seo
from fil.pages.picture_credits import pictures_credit as credit_for_pictures
from fil.stages import exercises


class UncreditedPicture(ValueError):
    """A picture question shows a picture whose source the credit line could not name."""


def write(pages: Path, sets: exercises.ExerciseSets, texts: Mapping[str, dict], published: Collection[str],
          pictures: Sequence[NounPicture]) -> list[Path]:
    """The questions' shards, the hub and a page per kind; the pages written. `pictures` are the noun
    pictures the picture questions may show: the pages that ask them credit their sets."""
    if not sets.kinds():
        return []
    counts = sets.counts()
    shards = exercises.write(pages, sets)
    credit = pictures_credit(sets, pictures)
    written = []
    for language in _languages():
        written.append(_write(pages, seo.exercise_index_path(language.code),
                              exercise_render.hub_page(language, texts, counts, shards, published=published,
                                                       picture_credit=credit)))
        written += [_write(pages, exercise_render.kind_path(language.code, kind, texts),
                           exercise_render.kind_page(kind, language, texts, counts, shards, published=published,
                                                     picture_credit=credit if kind == PICTURE else ""))
                    for kind in sets.kinds()]
    return written


def pictures_credit(sets: exercises.ExerciseSets, pictures: Sequence[NounPicture]) -> str:
    """The footer credit owed for the pictures the picture questions show (the hub mixes them in too)."""
    by_file = {picture.file_name: picture for picture in pictures}
    shown = [exercise.picture for exercise in sets.by_kind.get(PICTURE, ()) if exercise.picture]
    unknown = sorted({picture for picture in shown if PurePosixPath(picture).name not in by_file})
    if unknown:
        raise UncreditedPicture(f"{len(unknown)} picture questions show a picture of no known source, e.g. {unknown[:3]}")
    return credit_for_pictures(by_file[PurePosixPath(picture).name] for picture in shown)


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
