"""Tests for the pure row-shaping in packaging (no files, no SQLite)."""

from fil.packaging import conjugation_rows, gloss_rows, verb_row

_RECORD = {
    "id": "k-t-b_I",
    "root": "ك ت ب",
    "form": 1,
    "glosses": {"en": "to write", "bs": "pisati"},
    "past3ms": "كَتَبَ",
    "ayat": ["2:187"],
    "conjugation": {
        "past": {"huwa": "كَتَبَ", "ana": "كَتَبْتُ"},
        "imperative": {"anta": "اُكْتُبْ"},
    },
}


def test_verb_row_maps_fields():
    row = verb_row(_RECORD)
    assert row.verb_id == "k-t-b_I"
    assert row.form_number == 1
    assert row.dictionary_form == "كَتَبَ"
    assert row.ayat == "2:187"  # list joined into a string


def test_gloss_rows_one_per_language():
    rows = gloss_rows(_RECORD)
    assert {(r.lang, r.text) for r in rows} == {("en", "to write"), ("bs", "pisati")}
    assert all(r.verb_id == "k-t-b_I" for r in rows)


def test_conjugation_rows_bind_audio_by_structural_key():
    # Inject a fake hasher so the logic is testable without any real file.
    fake_hash = lambda audio_file: f"hash({audio_file})"
    rows = conjugation_rows(_RECORD, fake_hash)

    assert len(rows) == 3  # 2 past + 1 imperative
    huwa = next(r for r in rows if r.tense == "past" and r.pronoun == "huwa")
    assert huwa.arabic == "كَتَبَ"
    # The audio file is derived from the structural key — no chance of mis-binding.
    assert huwa.audio_file == "k-t-b_I__past__huwa.m4a"
    assert huwa.audio_sha256 == "hash(k-t-b_I__past__huwa.m4a)"
