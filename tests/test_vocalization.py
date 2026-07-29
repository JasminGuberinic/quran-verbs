"""Tests for the vocalization completeness helpers."""

from fil.vocalization import has_vocalized_ending, with_pausal_sukun


def test_adds_sukun_to_bare_final_consonant():
    # كَتَبْتُم (bare final mīm) -> كَتَبْتُمْ
    assert with_pausal_sukun("كَتَبْتُم") == "كَتَبْتُمْ"


def test_leaves_a_harakah_ending_untouched():
    assert with_pausal_sukun("كَتَبَ") == "كَتَبَ"


def test_leaves_a_long_vowel_ending_untouched():
    # ends in alif — must NOT get a sukūn
    assert with_pausal_sukun("كَتَبَا") == "كَتَبَا"
    assert with_pausal_sukun("كَتَبُوا") == "كَتَبُوا"


def test_has_vocalized_ending_detects_the_bare_consonant():
    assert has_vocalized_ending("كَتَبْتُم") is False   # bare final mīm
    assert has_vocalized_ending("كَتَبْتُمْ") is True    # after sukūn
    assert has_vocalized_ending("كَتَبَا") is True        # long vowel
    assert has_vocalized_ending("اُكْتُبْ") is True        # ends in sukūn
