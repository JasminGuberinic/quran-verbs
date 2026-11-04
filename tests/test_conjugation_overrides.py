"""Documented spellings: parsed strictly, looked up per cell, never silent."""

import pytest

from fil.conjugation_overrides import (
    OverrideFormatError,
    SpellingOverride,
    UnusedForm,
    documented_spellings,
    is_unused,
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
    {"وذر_1": {"past:*": {"unused": True}}},                                     # unused, but why?
    {"وذر_1": {"past:*": {"unused": True, "spellings": ["وَذَرَ"], "why": "w"}}},  # unused yet spelled
    {"وذر_1": {"past:*": {"spellings": ["وَذَرَ"], "why": "w"}}},                # one spelling for a tense
])
def test_a_malformed_or_undocumented_override_fails_fast(raw):
    with pytest.raises(OverrideFormatError):
        parse_overrides(raw)


def test_a_whole_tense_can_be_documented_as_unused():
    overrides = parse_overrides({"وذر_1": {"past:*": {"unused": True, "why": "its past is abandoned"}}})

    assert overrides[("وذر", 1)][("past", "*")] == UnusedForm("its past is abandoned")
    assert is_unused(overrides, "وذر", 1, "past", "ana") and is_unused(overrides, "وذر", 1, "past", "huwa")
    assert not is_unused(overrides, "وذر", 1, "present", "huwa")
    assert documented_spellings(overrides, "وذر", 1, "past", "ana") == ()


def test_a_single_cell_can_be_documented_as_unused():
    overrides = parse_overrides({"ودع_1": {"past:huwa": {"unused": True, "why": "w"}}})

    assert is_unused(overrides, "ودع", 1, "past", "huwa")
    assert not is_unused(overrides, "ودع", 1, "past", "hum")
    assert not is_unused(parse_overrides(_RAW), "سأل", 1, "imperative", "anta")
