"""Ayah quotations in our texts: English only in the shipped translation's words, Bosnian only our own.

Sahih International and Korkut are under copyright; earlier batches quoted them. The gate
(fil.ayah_quotes) holds every double-quoted passage to the convention, and the data tests run it
over every file that quotes ayat, so a later batch cannot bring a copyrighted rendering back.
"""

import pytest

from fil import ayah_quotes
from fil.resources import AYAH_TRANSLATIONS_DIR, NUANCE_GROUPS_JSON, PARTICLES_JSON, PRONOUNS_JSON, ROOT_CORE_IDEAS_JSON
from fil.stages import quotations

ENGLISH = {
    (7, 43): "And We remove whatever rancour may be in their hearts. Rivers flow beneath them.",
    (107, 4): "Ah, woe unto worshippers",
    (107, 5): "Who are heedless of their prayer;",
    (70, 18): "And hoarded (wealth) and withheld it.",
}
OWN = {"ayahQuotes": {"bs": "own"}}


def _entry(en: str, bs: str = "Bez navoda.", ref: str = "7:43", **extra) -> dict:
    return {"g": {**extra, "members": [{"ayat": [{"ref": ref, "why": {"en": en, "bs": bs}}]}]}}


def test_a_fragment_of_the_shipped_english_passes() -> None:
    entries = _entry("“We remove whatever rancour may be in their hearts” – the word is غِلّ.")
    assert ayah_quotes.problems(entries, ENGLISH) == []


def test_case_punctuation_brackets_and_ellipses_are_ignored() -> None:
    entries = _entry("“…and hoarded and withheld it” and “And hoarded (wealth) [it is wealth]…”", ref="70:18:1")
    assert ayah_quotes.problems(entries, ENGLISH) == []


def test_a_sahih_international_rendering_fails() -> None:
    entries = _entry("“And We will have removed whatever is within their breasts of resentment”")
    [problem] = ayah_quotes.problems(entries, ENGLISH)
    assert "not the shipped English (Pickthall) of 7:43" in problem


def test_a_quotation_may_run_into_the_next_ayah_named_inside_it() -> None:
    entries = _entry("“Ah, woe unto worshippers (107:5) who are heedless of their prayer”", ref="107:4")
    assert ayah_quotes.problems(entries, ENGLISH) == []


def test_a_reference_written_in_the_text_names_the_ayah() -> None:
    entries = {"g": {"tellApart": {"en": "the hoarder (“and withheld it”, 70:18)", "bs": "škrtac"}}}
    assert ayah_quotes.problems(entries, ENGLISH) == []


def test_a_word_inside_another_word_is_not_a_quotation_of_it() -> None:
    entries = _entry("“woe unto worship”", ref="107:4")
    assert ayah_quotes.problems(entries, ENGLISH)


def test_double_quotes_without_an_ayah_must_be_single_quoted_glosses() -> None:
    entries = {"g": {"title": {"en": "Subject: “He is…”", "bs": "Subjekat: ‚On je…‘"}}}
    [problem] = ayah_quotes.problems(entries, ENGLISH)
    assert "single quotation marks" in problem
    glossed = {"g": {"title": {"en": "Subject: ‘He is…’", "bs": "Subjekat: ‚On je…‘"}}}
    assert ayah_quotes.problems(glossed, ENGLISH) == []


def test_a_bosnian_quotation_must_be_declared_our_own_translation() -> None:
    quoted = "„I Mi ćemo iz njihovih srca ukloniti svaku mržnju“"
    [problem] = ayah_quotes.problems(_entry("No quotation.", quoted), ENGLISH)
    assert "our own translation" in problem
    assert ayah_quotes.problems(_entry("No quotation.", quoted, **OWN), ENGLISH) == []


def test_reviewer_notes_are_not_learner_texts() -> None:
    entries = {"g": {"notes": ["Sahih has “something else”"], "title": {"en": "Title", "bs": "Naslov"}}}
    assert ayah_quotes.problems(entries, ENGLISH) == []


def test_references_cover_words_and_runs() -> None:
    assert ayah_quotes.references_in("70:18:2 and 2:5–7") == ((70, 18), (2, 5), (2, 6), (2, 7))


needs_translation = pytest.mark.skipif(not (AYAH_TRANSLATIONS_DIR / "en.pickthall.txt").exists(),
                                       reason="the shipped English translation is not fetched")


@needs_translation
@pytest.mark.parametrize("path", [NUANCE_GROUPS_JSON, PARTICLES_JSON, PRONOUNS_JSON, ROOT_CORE_IDEAS_JSON], ids=lambda path: path.name)
def test_every_ayah_quoted_in_the_data_is_the_shipped_english_or_our_own_bosnian(path) -> None:
    assert quotations.problems_in(path) == []
