"""Tests for the study-site stage's pure views."""

from fil.examples import Example, ExampleWord
from fil.stages.site import _sentence_view


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
