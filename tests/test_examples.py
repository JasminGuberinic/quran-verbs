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


def test_a_form_the_analyzer_cannot_read_is_confirmed_by_the_corpus_table():
    # CAMeL reads the imperative ٱعْلَمْ as "I know"; the engine's own table has it exactly.
    from fil.examples import check_example, spelling_key
    word = ExampleWord("اعْلَمْ", "know", "znaj", is_target=True)
    draft = Example("اعْلَمْ", (word,), en="Know.", bs="Znaj.", tense="imperative", pronoun="anta")
    reads_as_first_person = lambda _w: [{"pos": "verb", "root": "ع.ل.م", "asp": "i", "per": "1"}]  # noqa: E731

    checks = check_example(draft, "علم", {"asp": "c", "per": "2"}, reads_as_first_person,
                           table_forms=frozenset({spelling_key("ٱعْلَمْ")}))

    assert checks.verb_form is True and checks.verb_form_by == "corpus table"


def test_a_documented_exception_passes_a_gloss_and_says_so():
    from fil.examples import check_example
    word = ExampleWord("كَفَرَ", "disbelieved", "nije vjerovao", is_target=True)
    draft = Example("كَفَرَ", (word,), en="He disbelieved.", bs="Nije vjerovao.")
    modern_only = lambda _w: [{"pos": "verb", "root": "ك.ف.ر", "gloss": "blaspheme;renege_Islam+he;it_<verb>"}]  # noqa: E731

    refused = check_example(draft, "كفر", None, modern_only)
    excepted = check_example(draft, "كفر", None, modern_only, gloss_exceptions={"ك.ف.ر": ("disbelieve",)})

    assert refused.gloss_agreement is False
    assert excepted.gloss_agreement is True and excepted.glossed_by_exception == ("كَفَرَ",)
