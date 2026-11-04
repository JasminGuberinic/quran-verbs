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

import unicodedata
from dataclasses import dataclass, field, replace
from typing import Callable, Mapping

from fil import glosses

# Renderings in further languages, as (language code, text) pairs. A tuple rather than a
# dict so a word stays hashable and immutable. English and Bosnian are first-class fields:
# English is the language the lexicon checks, Bosnian the one a person reads. Everything
# here is a machine translation nobody has reviewed, and is presented as such.
Translations = tuple[tuple[str, str], ...]


def translation_in(translations: Translations, language: str) -> str | None:
    """The rendering in one language, or None when it has not been translated."""
    return next((text for code, text in translations if code == language), None)


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
    translations: Translations = ()  # further languages, unreviewed machine translation


@dataclass(frozen=True)
class ExampleChecks:
    """Honest, independent verification results for one sentence."""

    verb_root: bool
    verb_form: bool | None  # None when the intended tense/pronoun was not declared
    all_words_valid: bool
    gloss_agreement: bool | None = None  # None when the lexicon glosses nothing
    gloss_conflicts: tuple[str, ...] = ()  # the words whose declared meaning was not attested
    # Which instrument confirmed the form: "analyzer", or "corpus table" when the analyzer
    # cannot read the spelling at all (hamzat-wasl imperatives such as ٱعْلَمْ) and the
    # verb matches the engine's own table for that cell letter for letter.
    verb_form_by: str = ""
    # Words whose meaning passed only through a documented exception (data/gloss_exceptions.json),
    # never silently: the lexicon glosses some Quranic verbs in a modern sense only.
    glossed_by_exception: tuple[str, ...] = ()

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
    independent: bool = False  # did the reader have NO part in drafting this sentence?

    def __post_init__(self) -> None:
        """Refuse a verdict that approves something it has just found fault with.

        "approved with reservations" is how a review becomes decoration: the summary says
        yes, the detail says no, and only the summary is ever read downstream. Making the
        combination unconstructible is stronger than remembering not to write it.
        """
        if self.approved and not (self.grammar_ok and self.translation_ok and self.verb_usage_ok):
            raise ValueError(
                "a verdict cannot be approved while grammar, translation or verb usage fails"
            )
        if not self.approved and not self.note:
            raise ValueError("a refusal must say what is wrong — the repair is drafted from it")


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
    drafted_by: str = ""          # who wrote it — so a reader cannot secretly be its author
    translations: Translations = ()  # the sentence in further languages, unreviewed
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
    def independently_reviewed(self) -> bool:
        """Approved by a reader who had no hand in writing it — the verdict that counts.

        A sentence can be `reviewed` and still be waiting for this: the pass that drafted
        it may have judged it, which is worth something but is not a second opinion.
        """
        return bool(self.critique and self.critique.approved and self.critique.independent)

    @property
    def is_shippable(self) -> bool:
        """Whether a learner may ever see it — nothing rejected or unchecked ships."""
        return self.tier in _SHIPPABLE_TIERS


_SHIPPABLE_TIERS = frozenset({"checked", "reviewed"})


# Further English meanings accepted for a root, by its CAMeL spelling ("ك.ف.ر"), each with
# the reason it is needed. Documented exceptions, not a way around the check.
# Where the analyzer reads a word only under the wrong root (تُبْ "repent!" only as تَبَّ
# "perish"), a root-level exception would be filed under that wrong root; such a word is
# excepted by its own spelling instead, keyed by `spelling_exception_key`.
GlossExceptions = Mapping[str, tuple[str, ...]]

SPELLING_EXCEPTION_PREFIX = "spelling:"


def spelling_exception_key(word: str) -> str:
    """The GlossExceptions key that excepts exactly this spelling, under no root."""
    return SPELLING_EXCEPTION_PREFIX + spelling_key(word)


def check_example(
    example: Example, expected_root: str, expected_features: dict | None, analyze: Analyze,
    table_forms: frozenset[str] = frozenset(), gloss_exceptions: GlossExceptions | None = None,
) -> ExampleChecks:
    """Run the mechanical gate: root, (optional) form, every-word-valid, and glosses.

    `table_forms` are the spellings (by `spelling_key`) the engine's own conjugation table
    gives for the declared cell. They decide the form only where the analyzer has no
    reading of it at all — a second instrument, never a looser one: the verb must match
    the table letter for letter.
    """
    target = _target_word(example)
    if target is None:
        return ExampleChecks(verb_root=False, verb_form=None, all_words_valid=False)

    analyses = {word: analyze(word.arabic) for word in example.words}
    verb_analyses = [a for a in analyses[target] if a.get("pos") == "verb" and a.get("root")]
    gloss_agreement, gloss_conflicts, by_exception = _gloss_check(analyses, gloss_exceptions or {})
    root_ok = any(_root_matches(expected_root, a["root"]) for a in verb_analyses)
    form_ok = _form_check(verb_analyses, expected_root, expected_features)
    form_by = "analyzer" if form_ok else ""
    if form_ok is False and spelling_key(target.arabic) in table_forms:
        root_ok, form_ok, form_by = True, True, "corpus table"
    return ExampleChecks(
        verb_root=root_ok,
        verb_form=form_ok,
        all_words_valid=_all_words_valid(analyses, target, confirmed_by_table=form_by == "corpus table"),
        gloss_agreement=gloss_agreement,
        gloss_conflicts=gloss_conflicts,
        verb_form_by=form_by,
        glossed_by_exception=by_exception,
    )


def _all_words_valid(analyses: dict[ExampleWord, list[dict]], target: ExampleWord, confirmed_by_table: bool) -> bool:
    """Every word has a reading — the target's may come from the corpus table instead.

    The table is consulted exactly when the analyzer has no reading of the verb (أَطِيعُوا
    gets none at all), so demanding an analyzer reading of it too would undo the table's vote.
    """
    return all(word_analyses or (word is target and confirmed_by_table) for word, word_analyses in analyses.items())


def checked(
    example: Example, expected_root: str, expected_features: dict | None, analyze: Analyze,
    table_forms: frozenset[str] = frozenset(), gloss_exceptions: GlossExceptions | None = None,
) -> Example:
    """Return the example with its `checks` filled in by the gate."""
    return replace(example, checks=check_example(
        example, expected_root, expected_features, analyze, table_forms, gloss_exceptions))


_SILENT_MARKS = "ۣۜ۟۠ۡۢۤۥۦۧۨ۩۪ۭ۫۬ٓ"
_WASL_VOWELS = "\u064e\u064f\u0650"


def spelling_key(word: str) -> str:
    """A spelling with Quranic orthography folded to standard: the same word, written once.

    ٱعْلَمْ (Uthmani), اِعْلَمْ and اعْلَمْ are one imperative; the connecting alif's vowel and
    the Uthmani pause marks are not part of the word's identity.
    """
    # Canonical mark order first: "تَّ" may be typed shadda-then-fatha or fatha-then-shadda.
    word = unicodedata.normalize("NFD", word)
    word = "".join(char for char in word if char not in _SILENT_MARKS).replace("ٱ", "ا")
    if word.startswith("ا") and len(word) > 1 and word[1] in _WASL_VOWELS:
        word = "ا" + word[2:]
    return word


def _form_check(verb_analyses: list[dict], expected_root: str, features: dict | None) -> bool | None:
    if features is None:
        return None
    return any(
        _root_matches(expected_root, analysis["root"])
        and all(analysis.get(key) == value for key, value in features.items())
        for analysis in verb_analyses
    )


def _gloss_check(
    analyses: dict[ExampleWord, list[dict]], exceptions: GlossExceptions
) -> tuple[bool | None, tuple[str, ...], tuple[str, ...]]:
    """Compare every declared meaning with the lexicon's own, naming the disagreements.

    A word the lexicon refuses is tried once more against its root's documented
    exceptions; if it passes there, it is named in the third result so the record shows it.
    """
    verdicts = []
    by_exception = []
    for word, word_analyses in analyses.items():
        verdict = glosses.gloss_agrees(word.en, _lexicon_glosses(word_analyses))
        if verdict is False and glosses.gloss_agrees(word.en, _excepted(word, word_analyses, exceptions)):
            verdict = True
            by_exception.append(word.arabic)
        verdicts.append((word, verdict))
    judged = [verdict for _word, verdict in verdicts if verdict is not None]
    if not judged:
        return None, (), ()  # the lexicon had nothing to say about any word
    conflicts = tuple(word.arabic for word, verdict in verdicts if verdict is False)
    return not conflicts, conflicts, tuple(by_exception)


def _excepted(word: ExampleWord, word_analyses: list[dict], exceptions: GlossExceptions) -> list[str]:
    by_root = [gloss for analysis in word_analyses for gloss in exceptions.get(analysis.get("root", ""), ())]
    return [*by_root, *exceptions.get(spelling_exception_key(word.arabic), ())]


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
