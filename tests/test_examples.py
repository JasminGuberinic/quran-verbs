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


def test_a_spelling_exception_passes_only_that_spelling_whatever_root_the_analyzer_guesses():
    # CAMeL reads تُبْ (repent!) only as تَبَّ (perish); excepting the wrong root would
    # let "repent" through for every word of ت.ب.ب, so the exception names the spelling.
    from fil.examples import check_example, spelling_exception_key
    wrong_root = lambda _w: [{"pos": "verb", "root": "ت.ب.ب", "gloss": "perish"}]  # noqa: E731
    exceptions = {spelling_exception_key("تُبْ"): ("repent",)}

    def gloss_check(arabic: str):
        word = ExampleWord(arabic, "repent", "pokaj se", is_target=True)
        return check_example(Example(arabic, (word,), en="Repent.", bs="Pokaj se."), "توب", None,
                             wrong_root, gloss_exceptions=exceptions)

    assert gloss_check("تُبْ").gloss_agreement is True
    assert gloss_check("تُبْ").glossed_by_exception == ("تُبْ",)
    assert gloss_check("تَبَّ").gloss_agreement is False


def test_a_spelling_is_one_word_whatever_order_its_marks_were_typed_in():
    from fil.examples import spelling_key
    shadda_first, fatha_first = "اتَّقِ", "اتَّقِ"
    assert spelling_key(shadda_first) == spelling_key(fatha_first)


def test_a_target_with_no_reading_at_all_is_valid_when_the_table_confirms_it():
    # CAMeL has no analysis of the Form IV imperative أَطِيعُوا; the engine's table has it exactly.
    from fil.examples import check_example, spelling_key
    word = ExampleWord("أَطِيعُوا", "obey", "slušajte", is_target=True)
    draft = Example("أَطِيعُوا", (word,), en="Obey.", bs="Slušajte.", tense="imperative", pronoun="antum")
    no_reading = lambda _w: []  # noqa: E731

    confirmed = check_example(draft, "طوع", {"asp": "c", "per": "2"}, no_reading,
                              table_forms=frozenset({spelling_key("أَطِيعُوا۟")}))
    unconfirmed = check_example(draft, "طوع", {"asp": "c", "per": "2"}, no_reading)

    assert confirmed.all_words_valid is True and confirmed.verb_form_by == "corpus table"
    assert unconfirmed.all_words_valid is False
