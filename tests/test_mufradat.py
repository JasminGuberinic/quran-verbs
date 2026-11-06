"""ar-Rāġib's Mufradāt, read from its OpenITI text so claims made in his name are checked against it.

The parser is pure and tested on a text written in the OpenITI layout; the golden test reads the
downloaded text when it is there (build/ — it is never committed).
"""

from __future__ import annotations

import pytest

from fil import nuance_store
from fil.nuances.mufradat import BOOK_URI, parse, skeleton
from fil.stages.nuances import MUFRADAT_TEXT

needs_text = pytest.mark.skipif(not MUFRADAT_TEXT.exists(), reason="the Mufradāt text is not downloaded")

_BOOK = """######OpenITI#
#META# 020.BookTITLE	:: المفردات في غريب القرآن
#META#Header#End#
# | بسم الله الرحمن الرحيم
# PageV01P006 المفردات PageV01P001 = كتاب الألف =
# أتى : الإتيان مجئ بسهولة ، قال : @QB@ أتى أمر الله @QE@
~~والإتيان يقال PageV01P007 للمجيء | بالذات .
# قيل : هو القنب .
# أب : الأب المرعى . = كتاب الجيم = جاء : المجيء كالإتيان
~~لكن المجيء أعم .
# | كتاب الخاء
# خَشِيَ : الخشية خوف يشوبه تعظيم .
# | كتاب الطاء
# طمن : الطمأنينة السكون .
# | كتاب الواو
# ود : الود محبة الشيء ms025 وتمني كونه . @QB@ ودوا @QE@ ومنه الوداد .
~~ورد : الورد الماء . قال : @QB@ وبئس الورد @QE@
# ولد الولد المولود .
# | كتاب الياء
# اليم : اليم البحر .
# يقين : اليقين من صفة العلم .
"""


def test_entries_are_found_in_the_books_order_with_their_text():
    book = parse(_BOOK)
    assert [entry.headword for entry in book.entries] == ["أتى", "أب", "جاء", "خشي", "طمن", "ود", "ورد", "ولد", "يم", "يقين"]
    first = book.entries[0]
    assert first.text == "الإتيان مجئ بسهولة ، قال : ﴿ أتى أمر الله ﴾ والإتيان يقال للمجيء بالذات . قيل : هو القنب ."


def test_a_paragraph_that_only_looks_like_an_entry_stays_in_its_entry():
    assert "قيل" not in [entry.headword for entry in parse(_BOOK).entries]


def test_an_entry_run_on_mid_line_or_without_its_colon_is_found_by_its_definition():
    book = parse(_BOOK)
    assert book.entries_for("ودد")[0].text == "الود محبة الشيء وتمني كونه . ﴿ ودوا ﴾ ومنه الوداد ."
    assert book.entries_for("ورد")[0].text == "الورد الماء . قال : ﴿ وبئس الورد ﴾"
    assert book.entries_for("ولد")[0].text == "الولد المولود ."


def test_a_letters_first_entry_runs_on_after_the_letters_title():
    assert parse(_BOOK).entries_for("جيأ")[0].text == "المجيء كالإتيان لكن المجيء أعم ."


@pytest.mark.parametrize(("root", "headword"), [("أتي", "أتى"), ("جيأ", "جاء"), ("خشي", "خشي"), ("ودد", "ود"), ("يمم", "يم"),
                                              ("يقن", "يقين"), ("طمأن", "طمن")])
def test_a_corpus_root_finds_the_headword_however_the_book_spells_it(root, headword):
    assert [entry.headword for entry in parse(_BOOK).entries_for(root)] == [headword]


def test_the_skeleton_keeps_a_first_waw_apart_from_a_hamza():
    assert skeleton("ودد") != skeleton("أدد") and skeleton("أتي") == skeleton("أتى") == skeleton("اتي")


def test_entries_mentioning_a_word_ignore_harakat():
    assert [entry.headword for entry in parse(_BOOK).entries_mentioning("الْخَشْيَة")] == ["خشي"]


def test_a_text_without_entries_is_refused():
    with pytest.raises(ValueError, match="Mufradāt"):
        parse("######OpenITI#\n# just a line\n")


@needs_text
def test_golden_the_downloaded_book_holds_his_khashya_definition():
    book = parse(MUFRADAT_TEXT.read_text(encoding="utf-8"))
    assert len(book.entries) > 1500
    assert book.entries_for("خشي")[0].text.startswith("الخشية خوف يشوبه تعظيم وأكثر ما يكون ذلك عن علم")
    assert book.entries_for("خوف")[0].text.startswith("الخوف توقع مكروه عن أمارة مظنونة أو معلومة")


@needs_text
def test_golden_every_entry_a_group_records_as_read_is_in_the_book():
    headwords = {entry.headword for entry in parse(MUFRADAT_TEXT.read_text(encoding="utf-8")).entries}
    recorded = {(group.slug, headword) for group in nuance_store.load_groups() for record in group.verified
                if record.source.startswith(BOOK_URI) for headword in record.entries}
    assert recorded and {(slug, headword) for slug, headword in recorded if headword not in headwords} == set()
