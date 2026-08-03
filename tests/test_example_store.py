"""Tests for the practice-example JSON store (round-trip on a temp file)."""

from fil import example_store
from fil.examples import Example, ExampleChecks, ExampleWord


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
