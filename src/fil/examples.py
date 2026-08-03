"""Practice example sentences for a verb, with a layered correctness gate.

These are NOT Quranic text. Their job is to build a feel for the verb — a simple,
meaningful sentence with a word-by-word translation, the learned verb emphasised.
The verbs come from the Quran (and each verb also carries the ayah references where
it occurs), but the sentences are composed for practice and labelled as such.

Because composing a sentence needs a language model (the conjugators only inflect),
the sentence text is drafted by the AI operator. The engine's job is the CORRECTNESS
GATE. We do NOT claim a single "verified" bit — that would overclaim. Instead we
record honest, independent CHECKS, each automatable with a morphological analyzer:

  - verb_root       — the emphasised word is a verb of the expected root
  - verb_form       — …and in the intended tense + pronoun (None if not declared)
  - all_words_valid — EVERY word in the sentence is morphologically analyzable
                      (catches typos / non-words anywhere, not just in the verb)

Only a sentence that passes every applicable check is trustworthy for practice.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable

# A morphological analyzer: an Arabic word → its candidate analyses (dicts with at
# least "pos", "root", and feature keys like "asp"/"per"/"gen"/"num"). Injected so
# this module stays pure and testable.
Analyze = Callable[[str], list[dict]]


@dataclass(frozen=True)
class ExampleWord:
    """One word of a practice sentence, with its gloss in each language."""

    arabic: str
    en: str
    bs: str
    is_target: bool = False  # the verb being learned — emphasised in the UI


@dataclass(frozen=True)
class ExampleChecks:
    """Honest, independent verification results for one sentence."""

    verb_root: bool
    verb_form: bool | None  # None when the intended tense/pronoun was not declared
    all_words_valid: bool

    @property
    def passed(self) -> bool:
        """True only if every APPLICABLE check passed (form skipped if unknown)."""
        return self.verb_root and self.all_words_valid and self.verb_form is not False


@dataclass(frozen=True)
class Example:
    """A practice sentence: the Arabic, its words, translations, and check results."""

    arabic: str
    words: tuple[ExampleWord, ...]
    en: str
    bs: str
    tense: str | None = None      # the conjugation cell it demonstrates …
    pronoun: str | None = None    # … so we can check the verb is in that form
    source: str = "generated"     # composed for practice — NOT from the Quran
    checks: ExampleChecks | None = field(default=None)


def check_example(
    example: Example, expected_root: str, expected_features: dict | None, analyze: Analyze
) -> ExampleChecks:
    """Run the gate: root, (optional) form, and every-word-valid."""
    target = _target_word(example)
    if target is None:
        return ExampleChecks(verb_root=False, verb_form=None, all_words_valid=False)

    verb_analyses = [a for a in analyze(target.arabic) if a.get("pos") == "verb" and a.get("root")]
    return ExampleChecks(
        verb_root=any(_root_matches(expected_root, a["root"]) for a in verb_analyses),
        verb_form=_form_check(verb_analyses, expected_root, expected_features),
        all_words_valid=all(analyze(word.arabic) for word in example.words),
    )


def checked(
    example: Example, expected_root: str, expected_features: dict | None, analyze: Analyze
) -> Example:
    """Return the example with its `checks` filled in by the gate."""
    return replace(example, checks=check_example(example, expected_root, expected_features, analyze))


def _form_check(verb_analyses: list[dict], expected_root: str, features: dict | None) -> bool | None:
    if features is None:
        return None
    return any(
        _root_matches(expected_root, analysis["root"])
        and all(analysis.get(key) == value for key, value in features.items())
        for analysis in verb_analyses
    )


def _target_word(example: Example) -> ExampleWord | None:
    return next((word for word in example.words if word.is_target), None)


_SEPARATORS = ". -‏‎"
_WEAK_RADICAL = "#"  # CAMeL marks a hollow/weak radical with '#'


def _root_matches(qac_root: str, camel_root: str) -> bool:
    """Compare a QAC root ('قول') with a CAMeL one ('ق.#.ل').

    CAMeL writes a weak radical as '#', so we treat it as a wildcard — otherwise
    every hollow verb (قال, كان, …) would fail the gate.
    """
    expected = [char for char in qac_root if char not in _SEPARATORS]
    actual = [radical for radical in camel_root.split(".") if radical]
    if len(expected) != len(actual):
        return False
    return all(a == _WEAK_RADICAL or a == e for e, a in zip(expected, actual))
