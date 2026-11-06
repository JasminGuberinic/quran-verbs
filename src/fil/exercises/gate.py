"""The gate every exercise passes before it is written: one right answer, and no option that a
learner could fairly call right too.

  - exactly one option is right, and there are 2–4 options, all of one sort;
  - no two Arabic options are the same word as a reader sees it (ٱلْأَرْضِ and الْأَرْضِ are one);
  - no two meaning options share a content word in either language ("srce" and "srce, duša"), and no two
    meanings of one verb's forms are the same in either language ("you said": قُلْتَ and قُلْتِ);
  - no grammatical answer is offered twice;
  - a passage with a blank has the blank, one with a mark has the mark;
  - every text is in Bosnian and English, and every exercise practises at least one word;
  - no two exercises of a kind share a key.

The kind-specific rules (an adjective form that does not agree, an effect the particle does not
have) are the generators' (fil.exercises.*), which only ever take a distractor their rule proves
wrong; this gate holds what is true of every exercise. It runs in `fil pages` and in the tests;
an exercise that breaks it stops the build.

Pure.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from itertools import combinations

from fil.exercises.model import AGREEMENT, KINDS, NUANCE, ONE_VERB_MEANINGS, Bilingual, Exercise, InvalidExercise, Option
from fil.exercises.text import meanings_overlap, same_gloss, same_spelling

MIN_OPTIONS, MAX_OPTIONS = 2, 4
_BLANKED = (NUANCE, AGREEMENT)   # the kinds whose passage hides the word to find


def check(exercises: Iterable[Exercise]) -> None:
    """Raise InvalidExercise naming every problem of every exercise."""
    exercises = list(exercises)
    found = [*_duplicate_keys(exercises), *(f"{exercise.identity}: {problem}"
                                           for exercise in exercises for problem in problems(exercise))]
    if found:
        raise InvalidExercise(f"{len(found)} exercise problems, e.g. {found[:5]}")


def problems(exercise: Exercise) -> list[str]:
    """What is wrong with one exercise (nothing, for one that may be shown)."""
    return [*_shape_problems(exercise), *_option_problems(exercise), *_text_problems(exercise)]


def _duplicate_keys(exercises: Sequence[Exercise]) -> list[str]:
    counts = Counter(exercise.identity for exercise in exercises)
    return [f"{identity}: key used {count} times" for identity, count in counts.items() if count > 1]


def _shape_problems(exercise: Exercise) -> list[str]:
    found = []
    if exercise.kind not in KINDS:
        found.append(f"unknown kind {exercise.kind!r}")
    if not exercise.words:
        found.append("practises no word")
    if exercise.kind in _BLANKED and not any(segment.is_blank for segment in exercise.passage):
        found.append("the passage has no blank")
    if exercise.passage and exercise.kind not in _BLANKED and not any(segment.is_marked for segment in exercise.passage):
        found.append("the passage marks no word")
    return found


def _option_problems(exercise: Exercise) -> list[str]:
    options = exercise.options
    found = []
    if not MIN_OPTIONS <= len(options) <= MAX_OPTIONS:
        found.append(f"{len(options)} options (wanted {MIN_OPTIONS}–{MAX_OPTIONS})")
    right = sum(1 for option in options if option.is_correct)
    if right != 1:
        found.append(f"{right} right options (wanted exactly one)")
    sorts = {option.sort for option in options}
    if len(sorts) > 1:
        found.append(f"options of several sorts: {sorted(sorts)}")
    clashes = (_clash(first, second, exercise.kind) for first, second in combinations(options, 2))
    found += [clash for clash in clashes if clash]
    return found


def _clash(first: Option, second: Option, kind: str) -> str:
    """Why two options cannot both be offered ("" when they can)."""
    if first.arabic is not None and second.arabic is not None and same_spelling(first.arabic, second.arabic):
        return f"two options are one word: {first.arabic} / {second.arabic}"
    if first.meaning is not None and second.meaning is not None and _are_one_meaning(first.meaning, second.meaning, kind):
        return f"two meanings overlap: {first.meaning.en} / {second.meaning.en}"
    if first.code is not None and first.code == second.code:
        return f"the answer {first.code} is offered twice"
    return ""


def _are_one_meaning(first: Bilingual, second: Bilingual, kind: str) -> bool:
    """Meanings of one verb's forms share the verb ("rekao je" / "rekli su"): they clash only when they are
    the same meaning; meanings of different words clash on any shared content word."""
    return same_gloss(first, second) if kind in ONE_VERB_MEANINGS else meanings_overlap(first, second)


def _text_problems(exercise: Exercise) -> list[str]:
    texts: list[Bilingual] = [text for text in (exercise.translation, exercise.explanation, exercise.gloss) if text]
    texts += [option.meaning for option in exercise.options if option.meaning]
    return [f"a text is missing a language: {text}" for text in texts if not text.bs.strip() or not text.en.strip()]
