"""Tests for the study-site stage's pure views."""

from fil.examples import Example, ExampleWord
from fil.service import Cell
from fil.stages.site import _cell_view, _principal, _sentence_view
from fil.word_translations import NoWordTranslations


def test_a_sentence_offers_every_language_it_has():
    word = ExampleWord("قَالَ", "said", "rekao je", is_target=True, translations=(("tr", "dedi"),))
    example = Example("قَالَ", (word,), en="He said.", bs="Rekao je.", translations=(("tr", "Dedi."),))

    view = _sentence_view(example)

    assert view["translation"] == {"bs": "Rekao je.", "en": "He said.", "tr": "Dedi."}
    assert view["words"][0]["translation"]["tr"] == "dedi"


class _FakeSound:
    def __init__(self, verb_glosses: dict) -> None:
        self.verb_glosses = verb_glosses
        self.form_glosses: dict = {}
        self.word_translations = NoWordTranslations()

    @staticmethod
    def word(surah: int, ayah: int, word: int) -> str:
        return f"audio/{surah}-{ayah}-{word}.m4a"


def _example_word_view(verb_glosses: dict) -> dict:
    from fil.stages.site import _ayah_word_view
    from fil.study import QuranWord
    word = QuranWord(7, 15, 1, "قَالَ", frozenset({("قول", 1, "past")}))
    readings = {(7, 15, 1): [{"tense": "past", "pronoun": "huwa", "passive": False, "objects": []}]}
    return _ayah_word_view(word, ("قول", 1), {}, readings, _FakeSound(verb_glosses))


def test_an_example_verb_with_its_gloss_shows_it():
    view = _example_word_view({"7:15:1": {"en": "he said", "bs": "rekao je"}})

    assert view["gloss"] == {"en": "he said", "bs": "rekao je"} and "grammar" not in view


def test_an_example_verb_not_yet_glossed_in_every_required_language_shows_its_grammar():
    view = _example_word_view({"7:15:1": {"bs": "rekao je"}})   # English missing

    assert view["gloss"] is None
    assert view["grammar"] == [{"tense": "past", "pronoun": "huwa", "passive": False, "objects": []}]
    assert view["audio"] == "audio/7-15-1.m4a"


def _cell(tense: str, pronoun: str, quran: bool = True, not_used: bool = False) -> dict:
    return {"tense": tense, "pronoun": pronoun, "quran": quran, "notUsed": not_used}


def test_principal_forms_prefer_the_third_person_singular():
    cells = [_cell("present", "hum"), _cell("past", "huwa")]
    assert _principal(cells) == [_cell("past", "huwa")]


def test_a_verb_without_principal_cells_is_shown_by_its_quranic_forms():
    cells = [_cell("present", "hum"), _cell("present", "antum"), _cell("past", "hum", quran=False)]
    assert _principal(cells) == [_cell("present", "hum"), _cell("present", "antum")]


def test_a_form_not_used_in_arabic_never_heads_a_card():
    # The past of وَذَرَ is documented as unused; the card is shown by what Arabic says.
    cells = [_cell("past", "huwa", quran=False, not_used=True), _cell("present", "huwa"), _cell("imperative", "anta")]
    assert _principal(cells) == [_cell("present", "huwa"), _cell("imperative", "anta")]


def test_a_cell_not_used_in_arabic_is_shown_marked_but_never_spoken():
    class Sound:
        def spoken(self, text):
            raise AssertionError(f"{text} must not be spoken")

    cell = Cell("imperative", "anta", "اِنْبَغِ", "generated", 0.7, None, generated_form="اِنْبَغِ",
                unused_why="impersonal")
    view = _cell_view(cell, {}, Sound())

    assert view["notUsed"] and view["plain"] == "اِنْبَغِ"
    assert view["spoken"] is None and view["recited"] is None


class _WordByWord:
    @staticmethod
    def of(location: tuple[int, int, int]) -> dict:
        return {"en": "they went"} if location == (2, 17, 3) else {}


def _form_view(translations=None) -> dict:
    from fil.attested_forms import AttestedForm, Grammar
    from fil.stages.site import _form_view as form_view
    grammar = Grammar("past", "hum", is_passive=False, objects=())
    sound = _FakeSound({})
    if translations:
        sound.word_translations = translations
    return form_view(("ذهب", 1), AttestedForm("ذَهَبَ", ((2, 17, 3), (7, 1, 2)), (grammar,)), sound)


def test_a_form_plays_its_recitation_at_its_first_occurrence():
    view = _form_view()

    assert view["first"] == "2:17" and view["audio"] == "audio/2-17-3.m4a"
    assert "gloss" not in view and "wordTranslation" not in view   # absent, never empty: rows stay lean


def test_a_form_carries_a_word_by_word_translation_when_a_source_gives_one():
    assert _form_view(_WordByWord())["wordTranslation"] == {"en": "they went"}
