"""The languages the site offers: one configured list, everything else dormant."""

import pytest

from fil import languages
from fil.languages import ACTIVE, CODES, KNOWN, LANGUAGES, REQUIRED, only_active

OFFERED = ("bs", "en", "tr", "fr", "id", "ur", "bn", "fa")
DORMANT = ("de", "sq", "ru", "ms", "es", "sw", "so", "hi")


def test_the_site_offers_exactly_the_supported_languages_in_picker_order():
    assert ACTIVE == OFFERED
    assert CODES == OFFERED
    assert tuple(language.code for language in LANGUAGES) == OFFERED


def test_dormant_languages_are_still_known_so_they_can_come_back():
    known = {language.code for language in KNOWN}
    assert set(DORMANT) <= known
    assert not set(DORMANT) & set(CODES)


def test_every_language_a_verb_must_have_is_offered():
    assert set(REQUIRED) <= set(ACTIVE)


def test_right_to_left_languages_keep_their_direction():
    assert {language.code for language in LANGUAGES if language.is_rtl} == {"ur", "fa"}


def test_only_active_keeps_the_offered_languages_and_drops_the_dormant_ones():
    glosses = {"bs": "reći", "en": "to say", "de": "sagen", "sw": "kusema", "fa": "گفتن"}

    assert only_active(glosses) == {"bs": "reći", "en": "to say", "fa": "گفتن"}


def test_an_active_language_that_is_not_known_fails_fast(monkeypatch):
    monkeypatch.setattr(languages, "ACTIVE", ("bs", "xx"))

    with pytest.raises(ValueError, match="xx"):
        languages._active_languages()
