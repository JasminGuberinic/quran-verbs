"""Tests for the study-site stage's pure views."""

from fil.examples import Example, ExampleWord
from fil.stages.site import _principal, _sentence_view


def test_a_sentence_offers_every_language_it_has():
    word = ExampleWord("قَالَ", "said", "rekao je", is_target=True, translations=(("tr", "dedi"),))
    example = Example("قَالَ", (word,), en="He said.", bs="Rekao je.", translations=(("tr", "Dedi."),))

    view = _sentence_view(example)

    assert view["translation"] == {"bs": "Rekao je.", "en": "He said.", "tr": "Dedi."}
    assert view["words"][0]["translation"]["tr"] == "dedi"


def test_an_ayah_verb_without_its_translation_fails_the_build():
    import pytest
    from fil.stages.site import MissingVerbGloss, _gloss_of
    from fil.study import QuranWord
    word = QuranWord(7, 15, 1, "قَالَ")

    with pytest.raises(MissingVerbGloss):
        _gloss_of(word, {"7:15:1": {"bs": "rekao je"}})   # other languages missing


def _cell(tense: str, pronoun: str, quran: bool = True) -> dict:
    return {"tense": tense, "pronoun": pronoun, "quran": quran}


def test_principal_forms_prefer_the_third_person_singular():
    cells = [_cell("present", "hum"), _cell("past", "huwa")]
    assert _principal(cells) == [_cell("past", "huwa")]


def test_a_verb_without_principal_cells_is_shown_by_its_quranic_forms():
    cells = [_cell("present", "hum"), _cell("present", "antum"), _cell("past", "hum", quran=False)]
    assert _principal(cells) == [_cell("present", "hum"), _cell("present", "antum")]
