"""Tests for diacritic-faithful speech: text preparation and the independent reading."""

import pytest

from fil.speech import expected_phonemes, normalized, prepared, verdict


@pytest.mark.parametrize("text, sounds", [
    ("يُكَذِّبُ", "y u k a * * i b u"),          # the shadda doubles; final vowel kept
    ("يُؤْتِي", "y u < t ii"),                     # long ī
    ("آتِ", "< aa t i"),                           # must not sound like يُؤْتِي
    ("كَانَ", "k aa n a"),                         # the model's own reader says "kana"
    ("نَتَّبِعُ", "n a t t a b i E u"),            # the model's own reader says "net"
    ("قَالُوا", "q aa l uu"),                      # the alif after the plural wāw is silent
    ("خَيْرًا", "x a y r a n"),                    # the alif after tanwīn is silent
    ("ٱتَّبَعَ", "< i t t a b a E a"),            # a connecting alif voiced at the start
    ("ٱدْعُ", "< u d E u"),                        # …with u when the next vowel is u
    ("كافِر", "k aa f i r"),                       # an unwritten fatha before alif
    ("هَذَا", "h aa * aa"),                        # the long ā print does not write
    ("ذَلِكَ", "* aa l i k a"),
    ("الْغَنِيُّ", "< a l g a n i y y u"),        # a doubled y, not a long ī
])
def test_words_are_read_as_their_vowels_say(text, sounds):
    assert " ".join(expected_phonemes(prepared(text))) == sounds


def test_the_article_joins_a_sun_letter_and_falls_silent_mid_sentence():
    reading = expected_phonemes(prepared("يَقُولُ الرَّسُولُ بِالْحَقِّ"))

    assert " ".join(reading) == "y a q uu l u + r r a s uu l u + b i l H a q q i"


def test_an_opening_article_is_voiced():
    assert " ".join(expected_phonemes(prepared("الشَّمْسُ"))) == "< a $ $ a m s u"


def test_allophones_and_doubling_are_normalized_away():
    assert normalized("y A q UU0 l u0 + rr a") == ["y", "a", "q", "uu", "l", "u", "+", "r", "r", "a"]


def test_a_reading_that_differs_from_the_model_is_not_faithful():
    model_says_kana = lambda text: "k a n a"  # noqa: E731 - the model's real bug
    assert not verdict("كَانَ", model_says_kana).is_faithful
    assert verdict("كَانَ", lambda text: "k aa n a").is_faithful


@pytest.mark.parametrize("text, sounds", [
    ("بِاللَّهِ", "b i l l aa h i"),              # bi-llāhi: one doubled l, long ā
    ("لِلَّهِ", "l i l l aa h i"),
    ("اللَّهُ", "< a l l aa h u"),
    ("يَعْلَمُ اللَّهُ", "y a E l a m u + l l aa h u"),
])
def test_the_name_of_god_is_read_with_its_long_a(text, sounds):
    assert " ".join(expected_phonemes(prepared(text))) == sounds
