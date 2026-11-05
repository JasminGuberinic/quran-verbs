"""Tests for diacritic-faithful speech: text preparation and the independent reading."""

import pytest

from fil.speech import (TtsArabicVoice, expected_phonemes, long_a_spelled_out, normalized, prepared,
                        shadda_first, verdict)


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
    ("يَسْـَٔلُ", "y a s < a l u"),                # Uthmani hamza seated on a tatweel
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


@pytest.mark.parametrize("text, sounds", [
    ("وَاسْمُ", "w a s m u"),                      # wa- before a connecting alif: no long ā
    ("شَيْـًٔا", "$ a y < a n"),                   # Uthmani hamza on a tatweel, with tanwīn
    ("قَوِيٌّ", "q a w i y y u n"),                # shadda and tanwīn on one letter
])
def test_more_words_are_read_as_their_vowels_say(text, sounds):
    assert " ".join(expected_phonemes(prepared(text))) == sounds


def test_a_long_vowel_before_its_own_glide_is_the_doubled_glide():
    assert normalized("q A w ii0 y u0 n") == ["q", "a", "w", "i", "y", "y", "u", "n"]
    assert normalized("E a d uu0 w u0 n") == ["E", "a", "d", "u", "w", "w", "u", "n"]


def test_the_shadda_is_handed_to_the_model_before_the_tanwin():
    assert shadda_first("قَوِيٌّ") == "قَوِيّ" + "ٌ"


@pytest.mark.parametrize("text, spelled", [
    ("وَاضِحٌ", "وَىضِحٌ"),                         # a long ā at the start of a word
    ("كَانَ", "كَىنَ"),
    ("أَبْوَابٌ", "أَبْوَىبٌ"),                      # the model's start-of-word marker is the letter b
    ("وَاسْمُ", "وَاسْمُ"),                         # a connecting alif stays
    ("صَاحِبُ", "صَاحِبُ"),                        # no ambiguity: untouched
])
def test_only_the_long_a_the_model_reads_short_is_spelled_out(text, spelled):
    assert long_a_spelled_out(text) == spelled


# The model's own phonetiser, as the second reader: its known slips must not cost a
# correct text its voice, and a real disagreement must still be caught.
@pytest.mark.parametrize("text", [
    "الْحَقُّ وَاضِحٌ",                 # "waDiH": the wā read short
    "صَوْتُ الْحَقِّ قَوِيٌّ",          # the tanwīn's n doubled instead of the y
    "سَقَى الْبُسْتَانِيُّ الْجَنَّةَ",  # ī+y for i-yy
    "صَنَعْتُ عَصِيرًا مِنَ الرُّمَّانِ",  # صَنَعْتُ matched the loan word "net"
    "عَدُوٌّ", "أَبْوَابٌ", "كَانَ", "وَاسْمُ", "شَيْـًٔا",
    "بِٱلَّيْلِ",                        # Uthmani drops the article's lām before lām: bi-l-layli
    "طَرِيقُ ٱلْهُدَىٰ", "ٱلْهُدَىٰ",      # final ىٰ is one long ā, not two
    "ٱلنَّبِىُّ", "اسْمُ ٱلنَّبِىِّ",      # undotted ى with shadda is the consonant yāʾ
])
def test_both_readers_agree_on_correct_texts(text):
    pytest.importorskip("tts_arabic.text")
    found = TtsArabicVoice().check(text)
    assert found.is_faithful, (found.expected, found.produced)


def test_the_second_reader_still_hears_a_short_a_as_short():
    pytest.importorskip("tts_arabic.text")
    assert normalized(TtsArabicVoice.phonemes("وَضَحَ")) == ["w", "a", "D", "a", "H", "a"]
    assert not verdict("وَضَحَ", lambda text: "w aa D a H a").is_faithful
