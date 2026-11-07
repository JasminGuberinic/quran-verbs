"""The Kaaba as a taught proper name, and the set phrases on a noun's card (fil.nouns.phrases):
الْمَسْجِدُ الْحَرَامُ on مَسْجِد — the reviewed data, its validation, the corpus places and the page."""

from __future__ import annotations

from html import escape

import pytest

from fil import noun_store
from fil.languages import LANGUAGES
from fil.nouns.model import ATTESTED, DEFINITE, GENERATED, INDEFINITE, NOUN, PROPER_NOUN, SINGULAR, Cell, NounLemma, NounOccurrence, ParadigmCell
from fil.nouns.phrases import InvalidPhraseData, grouped_by_writing, parse_phrases, phrase_places
from fil.nouns.selection import is_taught_proper_noun, skip_reason, taught_catalogue
from fil.nouns.studied import NounTable, TableRow
from fil.nouns.table import as_proper_name
from fil.pages import noun_render
from fil.pages.interface_text import load

KAABA = "كَعْبَة|كعب"
MASJID = "مَسْجِد|سجد"


def _lemma(lemma: str, root: str, kind: str, count: int, rank: int = 0) -> NounLemma:
    return NounLemma(lemma=lemma, root=root, kind=kind, gender="F", count=count, rank=rank, verb_form=None, plurals=(),
                     dual_count=0, forms=(), linked_verb=None, numbers=(SINGULAR,))


def _at(lemma: str, surah: int, ayah: int, word: int, text: str, case: str = "GEN") -> NounOccurrence:
    return NounOccurrence(surah=surah, ayah=ayah, word=word, word_text=text, stem=text, lemma=lemma, root="",
                          kind=NOUN, gender="M", number=SINGULAR, case=case, state=DEFINITE, verb_form=None, parts=None,
                          skip_reason=None)


# ---------------------------------------------------------------- the Kaaba, a taught proper name

def test_the_kaaba_is_the_one_proper_name_taught_on_a_noun_card():
    kaaba = _lemma("كَعْبَة", "كعب", PROPER_NOUN, 2)
    mecca = _lemma("مَكَّة", "مكك", PROPER_NOUN, 1)
    assert is_taught_proper_noun(kaaba) and skip_reason(kaaba) is None
    assert not is_taught_proper_noun(mecca) and skip_reason(mecca) == "proper name"


def test_a_taught_name_comes_after_the_common_nouns_ranked_by_its_frequency_among_them():
    common = [_lemma("يَوْم", "يوم", NOUN, 400, 1), _lemma("بَيْت", "بيت", NOUN, 70, 2), _lemma("ثَلْج", "ثلج", NOUN, 1, 3)]
    names = [_lemma("كَعْبَة", "كعب", PROPER_NOUN, 2, 7), _lemma("مَكَّة", "مكك", PROPER_NOUN, 1, 9)]
    taught = taught_catalogue([*common, *names])
    assert [lemma.lemma for lemma in taught] == ["يَوْم", "بَيْت", "ثَلْج", "كَعْبَة"]   # slugs of common nouns never move
    assert taught[-1].rank == 3


def test_a_proper_names_table_shows_only_its_definite_cells():
    cells = (ParadigmCell(Cell(SINGULAR, DEFINITE, "ACC"), "ٱلْكَعْبَةَ", ATTESTED),
             ParadigmCell(Cell(SINGULAR, INDEFINITE, "ACC"), "كَعْبَةً", GENERATED))
    table = as_proper_name(NounTable(KAABA, (TableRow(SINGULAR, SINGULAR, None, cells),)))
    assert [found.cell.state for found in table.rows[0].cells] == [DEFINITE]


def test_the_stored_kaaba_is_studied_definite_only_with_four_reviewed_sentences():
    assert KAABA in {meaning.key for meaning in noun_store.load_meanings()}
    table = noun_store.load_tables()[KAABA]
    assert {found.cell.state for row in table.rows for found in row.cells} == {DEFINITE}
    roles = {sentence.role for sentence in noun_store.load_sentences()
             if sentence.key == KAABA and sentence.example.independently_reviewed}
    assert roles == {"subject", "object", "preposition", "possession"}


# ---------------------------------------------------------------- set phrases

def test_the_sacred_mosque_is_a_phrase_on_the_mosques_card_beside_the_kaabas_picture():
    phrase, = noun_store.load_phrases()[MASJID]
    assert (phrase.arabic, phrase.adjective, phrase.en, phrase.bs, phrase.picture) == (
        "الْمَسْجِدُ الْحَرَامُ", "حَرام|حرم", "the Sacred Mosque", "Časni hram", KAABA)


@pytest.mark.parametrize("entry, problem", [
    ({MASJID: []}, "a list"),
    ({MASJID: [{"ar": "الْمَسْجِدُ الْحَرَامُ", "adjective": "حَرام|حرم", "en": "the Sacred Mosque", "bs": "Časni hram"}]}, "why"),
    ({MASJID: [{"ar": "الْمَسْجِدُ", "adjective": "حَرام|حرم", "en": "x", "bs": "x", "why": "x"}]}, "one adjective"),
    ({MASJID: [{"ar": "الْمَسْجِدُ الْحَرَامُ", "adjective": "حَرام", "en": "x", "bs": "x", "why": "x"}]}, "lemma|root"),
])
def test_a_malformed_phrase_is_refused(entry, problem):
    with pytest.raises(InvalidPhraseData, match=problem):
        parse_phrases(entry)


def test_a_phrase_is_where_the_adjective_is_the_very_next_word():
    mosque = [_at("مَسْجِد", 2, 144, 13, "ٱلْمَسْجِدِ"), _at("مَسْجِد", 9, 28, 9, "ٱلْمَسْجِدَ", "ACC"),
              _at("مَسْجِد", 2, 114, 5, "مَسَٰجِدَ", "ACC"), _at("مَسْجِد", 2, 217, 17, "وَٱلْمَسْجِدِ")]
    sacred = [_at("حَرام", 2, 144, 14, "ٱلْحَرَامِ"), _at("حَرام", 9, 28, 10, "ٱلْحَرَامَ", "ACC"),
              _at("حَرام", 2, 217, 18, "ٱلْحَرَامِ"), _at("حَرام", 2, 114, 9, "ٱلْحَرَامِ"),
              _at("حَرام", 3, 1, 14, "ٱلْحَرَامِ")]
    places = phrase_places(mosque, sacred)
    assert [place.ref for place in places] == ["2:144", "2:217", "9:28"]
    assert [(written, len(found)) for written, found in grouped_by_writing(places)] == [
        (("ٱلْمَسْجِدِ", "ٱلْحَرَامِ"), 1), (("وَٱلْمَسْجِدِ", "ٱلْحَرَامِ"), 1), (("ٱلْمَسْجِدَ", "ٱلْحَرَامَ"), 1)]


def _language(code: str):
    return next(language for language in LANGUAGES if language.code == code)


def _card(phrases: list[dict]) -> dict:
    return {"key": MASJID, "slug": "masjid", "rank": 300, "lemma": "مَسْجِد", "root": "سجد", "kind": "noun", "gender": "M",
            "count": 28, "ayahCount": 27, "meaning": {"en": "mosque", "bs": "džamija"}, "verb": None, "picture": None,
            "pictureKey": None, "lemmaSpoken": None, "plurals": [], "table": [], "explanation": [], "sentences": [],
            "forms": [], "ayat": [], "ayatFile": "ayat/noun-masjid.json", "ayatTranslations": {"en": "ayat/noun-masjid.en.json"}, "relation": None,
            "phrases": phrases}


_SACRED_MOSQUE = {
    "arabic": "الْمَسْجِدُ الْحَرَامُ", "spoken": None, "meaning": {"en": "the Sacred Mosque", "bs": "Časni hram"},
    "count": 15, "ayahCount": 15, "picture": "pictures/kaba.svg", "pictureKey": "كَعْبَة|كعب",
    "pictureOf": {"slug": "kaba", "lemma": "كَعْبَة", "meaning": {"en": "Kaaba", "bs": "Kaba"}},
    "forms": [{"words": [{"arabic": "ٱلْمَسْجِدِ", "audio": None}, {"arabic": "ٱلْحَرَامِ", "audio": None}],
               "count": 11, "case": "GEN", "refs": ["2:144", "2:149"]}],
}


@pytest.mark.parametrize("code, title, meaning", [("bs", "Izrazi u Kur'anu", "Časni hram"),
                                                   ("en", "Phrases in the Quran", "the Sacred Mosque")])
def test_the_mosques_page_shows_the_sacred_mosque_with_the_kaaba_beside_it(code, title, meaning):
    page = noun_render.noun_page(_card([_SACRED_MOSQUE]), _language(code), load()[code], category="places")
    assert escape(title) in page and meaning in page and "الْمَسْجِدُ الْحَرَامُ" in page
    assert 'src="../../../pictures/kaba.svg"' in page and f'href="../../../{code}/' in page
    assert 'href="https://quran.com/2/149"' in page


def test_a_card_without_phrases_has_no_phrase_section():
    page = noun_render.noun_page(_card([]), _language("en"), load()["en"], category="places")
    assert 'id="phrases"' not in page
def test_a_proper_names_page_shows_no_empty_indefinite_row_and_says_why():
    card = {**_card([]), "kind": "proper_noun", "table": [{"row": "S", "number": "S", "plural": None, "cells": [
        {"state": "definite", "case": "GEN", "text": "ٱلْكَعْبَةِ", "source": "attested", "audio": None}]}]}
    page = noun_render.noun_page(card, _language("en"), load()["en"], category="faith_hereafter")
    assert "no indefinite forms" in page and "<small>indefinite</small>" not in page


def test_a_page_owes_the_credit_for_the_picture_beside_a_phrase():
    from fil.noun_pictures import load_pictures
    from fil.stages.noun_pages import credits

    credit = credits([picture for picture in load_pictures() if picture.has_picture])
    assert "Twemoji" in credit([_card([_SACRED_MOSQUE])])
    assert credit([_card([])]) == ""
