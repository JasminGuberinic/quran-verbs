"""Tests for the study-site stage's pure views."""

from fil.examples import Example, ExampleWord
from fil.stages.site import _sentence_view


def test_a_sentence_offers_every_language_it_has():
    word = ExampleWord("قَالَ", "said", "rekao je", is_target=True, translations=(("tr", "dedi"),))
    example = Example("قَالَ", (word,), en="He said.", bs="Rekao je.", translations=(("tr", "Dedi."),))

    view = _sentence_view(example)

    assert view["translation"] == {"bs": "Rekao je.", "en": "He said.", "tr": "Dedi."}
    assert view["words"][0]["translation"]["tr"] == "dedi"
