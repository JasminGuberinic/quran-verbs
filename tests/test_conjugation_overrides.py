"""Documented spellings: parsed strictly, looked up per cell, never silent."""

import pytest

from fil.conjugation_overrides import (
    OverrideFormatError,
    SpellingOverride,
    documented_spellings,
    parse_overrides,
)

_RAW = {"سأل_1": {"imperative:anta": {"spellings": ["اِسْأَلْ", "سَلْ"], "why": "generator skips it"}}}


def test_an_override_is_found_by_its_verb_and_cell():
    overrides = parse_overrides(_RAW)

    assert overrides[("سأل", 1)][("imperative", "anta")] == SpellingOverride(("اِسْأَلْ", "سَلْ"), "generator skips it")
    assert documented_spellings(overrides, "سأل", 1, "imperative", "anta") == ("اِسْأَلْ", "سَلْ")


def test_a_cell_without_an_override_has_no_documented_spellings():
    overrides = parse_overrides(_RAW)

    assert documented_spellings(overrides, "سأل", 1, "past", "huwa") == ()
    assert documented_spellings(overrides, "قول", 1, "imperative", "anta") == ()


@pytest.mark.parametrize("raw", [
    {"سأل": {"imperative:anta": {"spellings": ["سَلْ"], "why": "w"}}},          # no form
    {"سأل_1": {"imperative": {"spellings": ["سَلْ"], "why": "w"}}},             # no pronoun
    {"سأل_1": {"imperative:anta": {"spellings": [], "why": "w"}}},               # nothing to offer
    {"سأل_1": {"imperative:anta": {"spellings": ["سَلْ"], "why": "  "}}},        # undocumented
])
def test_a_malformed_or_undocumented_override_fails_fast(raw):
    with pytest.raises(OverrideFormatError):
        parse_overrides(raw)
