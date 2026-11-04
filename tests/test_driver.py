"""Tests for present-vowel inference (fitting the generator to attested forms)."""

from fil.corpus.catalog import VerbEntry
from fil.driver import _infer_present_vowel, build_verb


def test_infers_damma_vowel_from_attested_present():
    # naṣara → yanṣuru: the attested present pins the stem vowel to ḍamma (u).
    vowel = _infer_present_vowel("نَصَرَ", {("present", "huwa"): "يَنصُرُ"})
    assert vowel == "u"


def test_returns_none_without_an_attested_present():
    # Only a past form attested → cannot infer the present vowel.
    assert _infer_present_vowel("نَصَرَ", {("past", "huwa"): "نَصَرَ"}) is None


def _entry(lemma: str) -> VerbEntry:
    return VerbEntry(root="_", form=1, lemma=lemma, occurrence_count=1, ayat=())


def test_a_documented_vowel_stands_in_when_the_corpus_shows_no_present():
    # قَرِبَ: every Quranic present is jussive, so nothing is attested to fit against.
    verb = build_verb(_entry("قَرِبَ"), {}, documented_vowel="a")
    assert verb is not None and verb.present_vowel == "a"


def test_the_fit_wins_over_a_documented_vowel():
    verb = build_verb(_entry("نَصَرَ"), {("present", "huwa"): "يَنصُرُ"}, documented_vowel="a")
    assert verb is not None and verb.present_vowel == "u"


def test_without_a_fit_or_a_record_there_is_no_verb_to_generate():
    assert build_verb(_entry("قَرِبَ"), {}) is None
