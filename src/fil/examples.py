"""Practice example sentences for a verb, with a layered correctness gate.

These are NOT Quranic text. Their job is to build a feel for the verb — a simple,
meaningful sentence with a word-by-word translation, the learned verb emphasised.
The verbs come from the Quran (and each verb also carries the ayah references where
it occurs), but the sentences are composed for practice and labelled as such.

Because composing a sentence needs a language model (the conjugators only inflect),
the sentence text is drafted by the AI operator. The engine's job is the CORRECTNESS
GATE. We do NOT claim a single "verified" bit — that would overclaim. Instead we
record honest, independent CHECKS, each one automatable with a morphological analyzer:

  - verb_root       — the emphasised word is a verb of the expected root
  - verb_form       — …and in the intended tense + pronoun (None if not declared)
  - all_words_valid — EVERY word in the sentence is morphologically analyzable
                      (catches typos / non-words anywhere, not just in the verb)
  - gloss_agreement — every word's declared meaning is one the LEXICON also gives it
                      (an independent vote on the translation; see fil.glosses)

Those four are mechanical, so they run on every sentence for free. What no analyzer
can judge is whether the sentence is natural, whether the grammar beyond the verb
holds together, and whether the whole translation says what the Arabic says. That
needs a language model or a human, so it is not computed here but RECORDED: a
`Critique` from a reviewer, whose identity is stored with the verdict.

Trust is therefore a tier, never a boolean — `Example.tier` reads:

    reviewed  — passed every applicable check AND an independent reviewer approved
    checked   — passed every applicable check, nobody has read it yet
    rejected  — a check failed, or a reviewer refused it
    unchecked — the gate has not run

Only `reviewed` is fully trustworthy; `rejected` must never reach a learner.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable

from fil import glosses

# A morphological analyzer: an Arabic word → its candidate analyses (dicts with at
# least "pos", "root", feature keys like "asp"/"per"/"gen"/"num", and — for the gloss
# check — "gloss"/"stemgloss"). Injected so this module stays pure and testable.
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
    gloss_agreement: bool | None = None  # None when the lexicon glosses nothing
    gloss_conflicts: tuple[str, ...] = ()  # the words whose declared meaning was not attested

    @property
    def passed(self) -> bool:
        """True only if every APPLICABLE check passed (an unknown check never fails)."""
        return (
            self.verb_root
            and self.all_words_valid
            and self.verb_form is not False
            and self.gloss_agreement is not False
        )


@dataclass(frozen=True)
class Critique:
    """A reviewer's verdict on what no analyzer can check — the judgement layer.

    `by` is part of the record on purpose. A verdict from the same pass that drafted
    the sentence is worth far less than one from an independent reviewer, and the
    stored data must show which of the two it is instead of flattening both into
    "approved". The engine never invents a critique; it only writes down the one given.
    """

    approved: bool
    grammar_ok: bool         # is the whole sentence correct MSA, not just the verb?
    translation_ok: bool     # do the en/bs renderings say what the Arabic says?
    verb_usage_ok: bool      # is the verb used the way the language really uses it?
    by: str                  # who judged (model or person) — honesty about independence
    note: str = ""           # what to fix, when refused


@dataclass(frozen=True)
class Example:
    """A practice sentence: the Arabic, its words, translations, and how far it is trusted."""

    arabic: str
    words: tuple[ExampleWord, ...]
    en: str
    bs: str
    tense: str | None = None      # the conjugation cell it demonstrates …
    pronoun: str | None = None    # … so we can check the verb is in that form
    source: str = "generated"     # composed for practice — NOT from the Quran
    checks: ExampleChecks | None = field(default=None)
    critique: Critique | None = field(default=None)

    @property
    def tier(self) -> str:
        """How far this sentence is trusted: reviewed > checked > unchecked | rejected."""
        if self.checks is None:
            return "unchecked"
        if not self.checks.passed:
            return "rejected"
        if self.critique is None:
            return "checked"
        return "reviewed" if self.critique.approved else "rejected"

    @property
    def is_shippable(self) -> bool:
        """Whether a learner may ever see it — nothing rejected or unchecked ships."""
        return self.tier in _SHIPPABLE_TIERS


_SHIPPABLE_TIERS = frozenset({"checked", "reviewed"})


def check_example(
    example: Example, expected_root: str, expected_features: dict | None, analyze: Analyze
) -> ExampleChecks:
    """Run the mechanical gate: root, (optional) form, every-word-valid, and glosses."""
    target = _target_word(example)
    if target is None:
        return ExampleChecks(verb_root=False, verb_form=None, all_words_valid=False)

    analyses = {word: analyze(word.arabic) for word in example.words}
    verb_analyses = [a for a in analyses[target] if a.get("pos") == "verb" and a.get("root")]
    gloss_agreement, gloss_conflicts = _gloss_check(analyses)
    return ExampleChecks(
        verb_root=any(_root_matches(expected_root, a["root"]) for a in verb_analyses),
        verb_form=_form_check(verb_analyses, expected_root, expected_features),
        all_words_valid=all(analyses.values()),
        gloss_agreement=gloss_agreement,
        gloss_conflicts=gloss_conflicts,
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


def _gloss_check(analyses: dict[ExampleWord, list[dict]]) -> tuple[bool | None, tuple[str, ...]]:
    """Compare every declared meaning with the lexicon's own, naming the disagreements."""
    verdicts = [
        (word, glosses.gloss_agrees(word.en, _lexicon_glosses(word_analyses)))
        for word, word_analyses in analyses.items()
    ]
    judged = [verdict for _word, verdict in verdicts if verdict is not None]
    if not judged:
        return None, ()  # the lexicon had nothing to say about any word
    conflicts = tuple(word.arabic for word, verdict in verdicts if verdict is False)
    return not conflicts, conflicts


def _lexicon_glosses(word_analyses: list[dict]) -> list[str]:
    """Every English gloss the analyzer offers for a word — inflected and lemma alike."""
    return [
        analysis[key]
        for analysis in word_analyses
        for key in ("gloss", "stemgloss")
        if analysis.get(key)
    ]


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
