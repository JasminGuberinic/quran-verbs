"""Tests for the per-language verb meanings."""

import json

import pytest

from fil.meanings import MissingMeaning, load


def test_meanings_load_in_the_promised_languages(tmp_path):
    path = tmp_path / "meanings.json"
    path.write_text(json.dumps({"قول_1": {"bs": "reći", "en": "to say"}}), encoding="utf-8")

    (meaning,) = load(path, languages=("bs", "en"))

    assert (meaning.root, meaning.form, meaning.gloss("en")) == ("قول", 1, "to say")


def test_a_missing_language_fails_the_build(tmp_path):
    # An empty card for a Turkish learner is a defect, not a gap to paper over.
    path = tmp_path / "meanings.json"
    path.write_text(json.dumps({"قول_1": {"bs": "reći", "en": ""}}), encoding="utf-8")

    with pytest.raises(MissingMeaning):
        load(path, languages=("bs", "en"))
