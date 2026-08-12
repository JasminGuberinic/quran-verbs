"""Tests for the practice-example correctness gate (pure — uses a fake analyzer)."""

from dataclasses import replace

from fil.examples import Critique, Example, ExampleChecks, ExampleWord, check_example, checked

_PAST_3MS = {"asp": "p", "per": "3", "gen": "m", "num": "s"}


def _example(target: str, *others: str) -> Example:
    words = (ExampleWord(target, "wrote", "napisao je", is_target=True),) + tuple(
        ExampleWord(word, "w", "r") for word in others
    )
    return Example(arabic=" ".join((target,) + others), words=words, en="…", bs="…")


def _analyze(mapping: dict[str, list[dict]]):
    """Fake analyzer: mapped words get their analyses; any other word is a valid noun."""
    return lambda word: mapping.get(word, [{"pos": "noun", "root": "x.y.z"}])


def test_verb_root_passes_when_it_matches():
    analyze = _analyze({"كَتَبَ": [{"pos": "verb", "root": "ك.ت.ب", **_PAST_3MS}]})
    checks = check_example(_example("كَتَبَ", "الدَّرْسَ"), "كتب", None, analyze)
    assert checks.verb_root and checks.all_words_valid and checks.passed


def test_verb_form_matches_declared_tense_and_pronoun():
    analyze = _analyze({"كَتَبَ": [{"pos": "verb", "root": "ك.ت.ب", **_PAST_3MS}]})
    checks = check_example(_example("كَتَبَ"), "كتب", _PAST_3MS, analyze)
    assert checks.verb_form is True and checks.passed


def test_verb_form_mismatch_fails():
    # Analysis says past-3ms, but we asked to demonstrate the present.
    analyze = _analyze({"كَتَبَ": [{"pos": "verb", "root": "ك.ت.ب", **_PAST_3MS}]})
    present = {"asp": "i", "per": "3", "gen": "m", "num": "s"}
    checks = check_example(_example("كَتَبَ"), "كتب", present, analyze)
    assert checks.verb_form is False and not checks.passed


def test_hollow_verb_matches_via_weak_radical_wildcard():
    analyze = _analyze({"قَالَ": [{"pos": "verb", "root": "ق.#.ل", **_PAST_3MS}]})
    checks = check_example(_example("قَالَ"), "قول", None, analyze)
    assert checks.verb_root


def test_wrong_root_fails():
    analyze = _analyze({"ذَهَبَ": [{"pos": "verb", "root": "ذ.ه.ب", **_PAST_3MS}]})
    assert not check_example(_example("ذَهَبَ"), "كتب", None, analyze).passed


def test_a_nonword_anywhere_fails_all_words_valid():
    analyze = _analyze({
        "كَتَبَ": [{"pos": "verb", "root": "ك.ت.ب", **_PAST_3MS}],
        "زقظ": [],  # a broken word → zero analyses
    })
    checks = check_example(_example("كَتَبَ", "زقظ"), "كتب", None, analyze)
    assert checks.verb_root and not checks.all_words_valid and not checks.passed


def test_no_target_word_fails():
    example = Example(
        arabic="الدَّرْسَ",
        words=(ExampleWord("الدَّرْسَ", "the lesson", "lekciju"),),
        en="", bs="",
    )
    assert not check_example(example, "كتب", None, lambda word: []).passed


def test_checked_attaches_the_results():
    analyze = _analyze({"كَتَبَ": [{"pos": "verb", "root": "ك.ت.ب", **_PAST_3MS}]})
    example = checked(_example("كَتَبَ"), "كتب", _PAST_3MS, analyze)
    assert example.checks is not None and example.checks.passed


def test_gloss_agreement_passes_when_the_lexicon_confirms_every_word():
    analyze = _analyze({
        "كَتَبَ": [{"pos": "verb", "root": "ك.ت.ب", "gloss": "wrote+he;it_<verb>", **_PAST_3MS}],
        "الدَّرْسَ": [{"pos": "noun", "root": "د.ر.س", "gloss": "the+lesson+[def.acc.]"}],
    })
    example = Example(
        arabic="كَتَبَ الدَّرْسَ",
        words=(
            ExampleWord("كَتَبَ", "wrote", "napisao je", is_target=True),
            ExampleWord("الدَّرْسَ", "the lesson", "lekciju"),
        ),
        en="wrote the lesson", bs="napisao lekciju",
    )
    checks = check_example(example, "كتب", None, analyze)

    assert checks.gloss_agreement is True and checks.gloss_conflicts == () and checks.passed


def test_a_word_that_does_not_mean_what_we_claim_fails_and_is_named():
    # Morphologically flawless, but "الصِّدْقَ" is sincerity — not "the truth".
    analyze = _analyze({
        "أَقُولُ": [{"pos": "verb", "root": "ق.#.ل", "gloss": "I+say", **_PAST_3MS}],
        "الصِّدْقَ": [{"pos": "noun", "root": "ص.د.ق", "gloss": "the+sincerity;candor"}],
    })
    example = Example(
        arabic="أَقُولُ الصِّدْقَ",
        words=(
            ExampleWord("أَقُولُ", "I say", "govorim", is_target=True),
            ExampleWord("الصِّدْقَ", "the truth", "istinu"),
        ),
        en="I say the truth", bs="Govorim istinu",
    )
    checks = check_example(example, "قول", None, analyze)

    assert checks.verb_root and checks.all_words_valid  # the morphology is fine …
    assert checks.gloss_agreement is False              # … the translation is not
    assert checks.gloss_conflicts == ("الصِّدْقَ",)
    assert not checks.passed


def test_a_lexicon_without_glosses_never_fails_the_sentence():
    analyze = _analyze({"كَتَبَ": [{"pos": "verb", "root": "ك.ت.ب", **_PAST_3MS}]})
    checks = check_example(_example("كَتَبَ", "الدَّرْسَ"), "كتب", None, analyze)

    assert checks.gloss_agreement is None and checks.passed


def test_tier_rises_from_unchecked_to_reviewed():
    passing = ExampleChecks(verb_root=True, verb_form=True, all_words_valid=True)
    example = _example("كَتَبَ")
    assert example.tier == "unchecked" and not example.is_shippable

    gated = replace(example, checks=passing)
    assert gated.tier == "checked" and gated.is_shippable

    approved = replace(gated, critique=_critique(approved=True))
    assert approved.tier == "reviewed" and approved.is_shippable


def test_a_reviewer_can_reject_a_sentence_the_analyzer_accepted():
    passing = ExampleChecks(verb_root=True, verb_form=True, all_words_valid=True)
    gated = replace(_example("كَتَبَ"), checks=passing)

    refused = replace(gated, critique=_critique(approved=False))

    assert refused.tier == "rejected" and not refused.is_shippable


def _critique(approved: bool) -> Critique:
    return Critique(
        approved=approved, grammar_ok=approved, translation_ok=approved,
        verb_usage_ok=approved, by="test-reviewer", note="" if approved else "unnatural",
    )
