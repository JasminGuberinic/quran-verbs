"""Tests for the practice-example JSON store (round-trip on a temp file)."""

from dataclasses import replace

from fil import example_store
from fil.examples import Critique, Example, ExampleChecks, ExampleWord, translation_in
from fil.example_store import load, save


def _example() -> Example:
    return Example(
        arabic="كَتَبَ الدَّرْسَ",
        words=(
            ExampleWord("كَتَبَ", "wrote", "napisao je", is_target=True),
            ExampleWord("الدَّرْسَ", "the lesson", "lekciju"),
        ),
        en="wrote the lesson", bs="napisao lekciju",
        tense="past", pronoun="huwa",
        checks=ExampleChecks(verb_root=True, verb_form=True, all_words_valid=True),
    )


def test_save_then_load_round_trips(tmp_path):
    path = tmp_path / "examples.json"
    example_store.save("كتب", 1, [_example()], path)

    loaded = example_store.load("كتب", 1, path)
    assert len(loaded) == 1
    assert loaded[0].arabic == "كَتَبَ الدَّرْسَ"
    assert loaded[0].words[0].is_target is True
    assert loaded[0].tense == "past" and loaded[0].pronoun == "huwa"
    assert loaded[0].checks is not None and loaded[0].checks.passed


def test_load_unknown_verb_is_empty(tmp_path):
    assert example_store.load("xyz", 1, tmp_path / "missing.json") == []


def test_a_reviewers_verdict_and_gloss_conflicts_survive_the_round_trip(tmp_path):
    path = tmp_path / "examples.json"
    reviewed = replace(
        _example(),
        checks=ExampleChecks(
            verb_root=True, verb_form=True, all_words_valid=True,
            gloss_agreement=False, gloss_conflicts=("الدَّرْسَ",),
        ),
        critique=Critique(
            approved=False, grammar_ok=True, translation_ok=False, verb_usage_ok=True,
            by="reviewer-under-test", note="the object does not mean that",
        ),
    )
    example_store.save("كتب", 1, [reviewed], path)

    loaded = example_store.load("كتب", 1, path)[0]
    assert loaded.checks.gloss_conflicts == ("الدَّرْسَ",)  # a JSON list, back as a tuple
    assert loaded.critique is not None and loaded.critique.by == "reviewer-under-test"
    assert loaded.tier == "rejected"


def test_examples_written_before_the_gloss_check_still_load(tmp_path):
    path = tmp_path / "examples.json"
    path.write_text(
        '{"كتب_1": [{"arabic": "كَتَبَ", "en": "wrote", "bs": "napisao", '
        '"words": [{"arabic": "كَتَبَ", "en": "wrote", "bs": "napisao", "is_target": true}], '
        '"checks": {"verb_root": true, "verb_form": null, "all_words_valid": true}}]}',
        encoding="utf-8",
    )

    loaded = example_store.load("كتب", 1, path)[0]

    assert loaded.checks.gloss_agreement is None and loaded.tier == "checked"


def test_translations_survive_a_round_trip(tmp_path):
    word = ExampleWord("قَالَ", "said", "rekao je", is_target=True,
                       translations=(("de", "sagte"), ("tr", "dedi")))
    example = Example(arabic="قَالَ", words=(word,), en="He said.", bs="Rekao je.",
                      translations=(("de", "Er sagte."), ("tr", "Dedi.")))

    save("قول", 1, [example], tmp_path / "ex.json")
    (loaded,) = load("قول", 1, tmp_path / "ex.json")

    assert loaded == example
    assert translation_in(loaded.words[0].translations, "tr") == "dedi"


def test_a_file_written_before_translations_existed_still_loads(tmp_path):
    path = tmp_path / "ex.json"
    path.write_text('{"قول_1": [{"arabic": "قَالَ", "en": "He said.", "bs": "Rekao je.", '
                    '"words": [{"arabic": "قَالَ", "en": "said", "bs": "rekao je", "is_target": true}]}]}',
                    encoding="utf-8")

    (loaded,) = load("قول", 1, path)

    assert loaded.translations == () and loaded.words[0].translations == ()
