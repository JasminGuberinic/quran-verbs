"""Tests that the Verb model fails fast on malformed authoring."""

import pytest

from fil.models import Verb

_VALID = dict(
    id="k-t-b_I", root="ك ت ب", past3ms="كَتَبَ", present_vowel="u",
    transitive=True, form=1, glosses={"en": "to write", "bs": "pisati"},
)


def test_valid_verb_constructs():
    assert Verb(**_VALID).id == "k-t-b_I"


def test_rejects_bad_present_vowel():
    with pytest.raises(ValueError, match="present_vowel"):
        Verb(**{**_VALID, "present_vowel": "x"})


def test_rejects_out_of_range_form():
    with pytest.raises(ValueError, match="form must be"):
        Verb(**{**_VALID, "form": 0})


def test_rejects_unvocalized_past3ms():
    # bare "كتب" has no tashkīl → must be rejected
    with pytest.raises(ValueError, match="tashkīl"):
        Verb(**{**_VALID, "past3ms": "كتب"})
