"""Tests for the practice-example correctness gate (pure — uses a fake analyzer)."""

from fil.examples import Example, ExampleWord, check_example, checked

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
