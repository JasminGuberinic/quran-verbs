"""Correctness tests for the conjugation engine — the religious-quality backbone.

Because this is a Quran-learning app, a wrong conjugation is unacceptable. These
tests encode the KNOWN-CORRECT classical forms as ground truth. If the generator
ever changes or regresses, these fail loudly. (Final release still gets a human
scholar review; these guarantee no silent regressions and enforce structure.)
"""

import pytest

from fil.conjugation import conjugate
from fil.models import Verb
from fil.vocalization import has_vocalized_ending

# ك-ت-ب "to write", Form I, yaktubu (ḍamma). Golden forms verified by hand.
KATABA = Verb(
    id="k-t-b_I", root="ك ت ب", past3ms="كَتَبَ", present_vowel="u",
    transitive=True, form=1, glosses={"en": "to write", "bs": "pisati"},
)

# ن-ص-ر "to help", Form I, yanṣuru (ḍamma).
NASARA = Verb(
    id="n-s-r_I", root="ن ص ر", past3ms="نَصَرَ", present_vowel="u",
    transitive=True, form=1, glosses={"en": "to help", "bs": "pomoći"},
)

# The 12 pronoun keys we teach, and the imperative's 2nd-person subset.
ALL_PRONOUNS = {
    "ana", "nahnu", "anta", "anti", "antuma", "antum",
    "antunna", "huwa", "hiya", "huma", "hum", "hunna",
}
IMPERATIVE_PRONOUNS = {"anta", "anti", "antuma", "antum", "antunna"}

# Harakāt / diacritics every fully-vocalized form must contain at least one of.
_TASHKIL = set("ًٌٍَُِّْ")  # ًٌٍَُِّْ


# ── Golden forms — exact ground truth for كتب ──────────────────────────────────

def test_kataba_past_is_exactly_correct():
    past = conjugate(KATABA)["past"]
    assert past["huwa"] == "كَتَبَ"
    assert past["hiya"] == "كَتَبَتْ"
    assert past["ana"] == "كَتَبْتُ"
    assert past["anta"] == "كَتَبْتَ"
    assert past["anti"] == "كَتَبْتِ"
    assert past["nahnu"] == "كَتَبْنَا"
    assert past["hum"] == "كَتَبُوا"
    assert past["hunna"] == "كَتَبْنَ"
    # Regression: the generator leaves a bare final mīm ("كَتَبْتُم"); the pipeline
    # must supply the pausal sukūn.
    assert past["antum"] == "كَتَبْتُمْ"


def test_kataba_present_is_exactly_correct():
    present = conjugate(KATABA)["present"]
    assert present["ana"] == "أَكْتُبُ"
    assert present["huwa"] == "يَكْتُبُ"
    assert present["hum"] == "يَكْتُبُونَ"


def test_kataba_imperative_is_exactly_correct():
    imperative = conjugate(KATABA)["imperative"]
    assert imperative["anta"] == "اُكْتُبْ"
    assert imperative["anti"] == "اُكْتُبِي"
    assert imperative["antum"] == "اُكْتُبُوا"


def test_nasara_anchor_forms():
    table = conjugate(NASARA)
    # The past 3ms must equal the dictionary form we fed in.
    assert table["past"]["huwa"] == "نَصَرَ"
    # Present 3ms of a ḍamma verb: yanṣuru.
    assert table["present"]["huwa"] == "يَنْصُرُ"


# ── Structural invariants — hold for EVERY verb we ever add ────────────────────

@pytest.mark.parametrize("verb", [KATABA, NASARA])
def test_all_pronoun_cells_present_for_past_and_present(verb):
    table = conjugate(verb)
    assert set(table["past"]) == ALL_PRONOUNS
    assert set(table["present"]) == ALL_PRONOUNS


@pytest.mark.parametrize("verb", [KATABA, NASARA])
def test_imperative_has_only_second_person(verb):
    assert set(conjugate(verb)["imperative"]) == IMPERATIVE_PRONOUNS


@pytest.mark.parametrize("verb", [KATABA, NASARA])
def test_every_form_is_nonempty_and_vocalized(verb):
    for tense in conjugate(verb).values():
        for form in tense.values():
            assert form, "a conjugated form must never be empty"
            assert _TASHKIL & set(form), f"form '{form}' has no tashkīl"


@pytest.mark.parametrize("verb", [KATABA, NASARA])
def test_every_form_has_a_vocalized_ending(verb):
    # The strong invariant: the FINAL letter must be voweled (a diacritic or a
    # long vowel) — this is what catches a bare final consonant.
    for tense in conjugate(verb).values():
        for form in tense.values():
            assert has_vocalized_ending(form), f"form '{form}' ends unvocalized"
