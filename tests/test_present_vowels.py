"""Hand-recorded present vowels: parsed strictly, used only where the corpus is silent."""

import pytest

from fil.present_vowels import (
    DocumentedVowel,
    PresentVowelFormatError,
    documented_vowel,
    parse_present_vowels,
)

_RAW = {"قرب_1": {"vowel": "a", "why": "only jussive presents"}}


def test_a_recorded_vowel_is_found_by_its_verb():
    vowels = parse_present_vowels(_RAW)

    assert vowels[("قرب", 1)] == DocumentedVowel("a", "only jussive presents")
    assert documented_vowel(vowels, "قرب", 1) == "a"


def test_a_verb_without_a_record_has_no_documented_vowel():
    assert documented_vowel(parse_present_vowels(_RAW), "نصر", 1) is None


@pytest.mark.parametrize("raw", [
    {"قرب": {"vowel": "a", "why": "w"}},       # no form
    {"قرب_2": {"vowel": "a", "why": "w"}},     # a derived form's pattern fixes its vowel
    {"قرب_1": {"vowel": "e", "why": "w"}},     # not a stem vowel
    {"قرب_1": {"why": "w"}},                   # no vowel at all
    {"قرب_1": {"vowel": "a", "why": "  "}},    # undocumented
])
def test_a_malformed_or_undocumented_vowel_fails_fast(raw):
    with pytest.raises(PresentVowelFormatError):
        parse_present_vowels(raw)
