"""Tests for present-vowel inference (fitting the generator to attested forms)."""

from fil.driver import _infer_present_vowel


def test_infers_damma_vowel_from_attested_present():
    # naṣara → yanṣuru: the attested present pins the stem vowel to ḍamma (u).
    vowel = _infer_present_vowel("نَصَرَ", {("present", "huwa"): "يَنصُرُ"})
    assert vowel == "u"


def test_returns_none_without_an_attested_present():
    # Only a past form attested → cannot infer the present vowel.
    assert _infer_present_vowel("نَصَرَ", {("past", "huwa"): "نَصَرَ"}) is None
