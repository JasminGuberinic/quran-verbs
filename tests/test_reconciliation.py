"""Tests for reconciliation tiers across the Quran + one or more generators."""

import pytest

from fil.reconciliation import agrees_across_join, forms_match, reconcile, tier_counts


def test_folds_alef_madda_against_hamza_alef():
    # آمَنَ (imlāʾī, alef-madda) ≡ ءَامَنَ (Uthmani, hamza + alef) — same form.
    assert forms_match("آمَنَ", "ءَامَنَ")


def test_folds_alef_maqsura_against_yaa():
    assert forms_match("قُولِي", "قُولِىٓ")


def test_still_flags_a_real_letter_difference():
    assert not forms_match("كَتَبَ", "كَتَنَ")


def test_superscript_alef_over_a_long_vowel_is_only_a_reading_aid():
    # يَرَىٰ (Uthmani) is the SAME form as يَرَى — the mark says "read this long", it is
    # not an extra letter. Treating it as one kept رأي out of the generator entirely.
    assert forms_match("يَرَىٰ", "يَرَى")
    assert forms_match("عَلَىٰ", "عَلَى")


def test_superscript_alef_over_a_consonant_stands_for_an_omitted_letter():
    # Here the mark replaces an alef that simply is not written, so it must count.
    assert forms_match("سَمَٰوَات", "سَمَاوَات")
    assert not forms_match("رَحْمَٰن", "رَحْمن")


def test_attested_cell_uses_truth_and_records_agreement():
    generated = {"past": {"hum": "كَتَبُوا", "huwa": "كَتَبَ"}}
    attested = {("past", "hum"): "كَتَبُوا"}  # Quran attests only 'hum'

    cells = reconcile([generated], attested)
    hum = next(c for c in cells if c.pronoun == "hum")
    huwa = next(c for c in cells if c.pronoun == "huwa")

    assert hum.source == "attested" and hum.generator_agrees is True
    assert hum.arabic == "كَتَبُوا" and hum.confidence == 1.0
    assert huwa.source == "generated" and huwa.generator_agrees is None


def test_generator_disagreement_quarantines_but_ships_the_truth():
    # A GENUINE difference (a wrong letter ب→ن), not mere orthography.
    generated = {"past": {"huwa": "كَتَنَ"}}
    attested = {("past", "huwa"): "كَتَبَ"}

    cell = reconcile([generated], attested)[0]
    assert cell.source == "quarantined"
    assert cell.generator_agrees is False
    assert cell.arabic == "كَتَبَ"          # truth wins
    assert cell.alternatives == ("كَتَنَ",)  # the disagreeing generator form, for review


def test_orthographic_differences_are_not_conflicts():
    # Uthmani (dagger alef) vs imlāʾī (full alef) is the SAME form, not a bug.
    generated = {"past": {"nahnu": "نَصَرْنَا"}}
    attested = {("past", "nahnu"): "نَصَرْنَٰ"}

    cell = reconcile([generated], attested)[0]
    assert cell.source == "attested"
    assert cell.generator_agrees is True


def test_two_generators_agreeing_off_quran_is_consensus():
    # Not attested by the Quran, but both independent generators agree.
    qutrub = {"present": {"huwa": "يَكْتُبُ"}}
    camel = {"present": {"huwa": "يَكْتُبُ"}}

    cell = reconcile([qutrub, camel], {})[0]
    assert cell.source == "consensus"
    assert cell.confidence == 0.9
    assert cell.quran_attested is False


def test_two_generators_disagreeing_off_quran_is_quarantined():
    qutrub = {"present": {"huwa": "يَكْتُبُ"}}
    camel = {"present": {"huwa": "يَكْتِبُ"}}  # different stem vowel

    cell = reconcile([qutrub, camel], {})[0]
    assert cell.source == "quarantined"
    assert cell.arabic == "يَكْتُبُ"          # ships the primary generator's form
    assert cell.alternatives == ("يَكْتِبُ",)  # the dissenting form, for review


def test_tier_counts_summarize():
    generated = {"past": {"hum": "كَتَبُوا", "huwa": "كَتَبَ", "antum": "x"}}
    attested = {("past", "hum"): "كَتَبُوا", ("past", "antum"): "y"}
    assert tier_counts(reconcile([generated], attested)) == {
        "attested": 1, "consensus": 0, "generated": 1, "quarantined": 1
    }


# --- Spellings at a word join: the Quran spells a word as joined to its neighbour ---


@pytest.mark.parametrize("generated, attested", [
    ("ذَرْ", "ذَرِ"),                    # helping kasra on a final sukūn (6:91)
    ("أَخَذَتْ", "أَخَذَتِ"),
    ("عَلِمْتُمْ", "عَلِمْتُمُ"),           # helping ḍamma on the plural mīm
    ("اِبْتَغَوْا", "ٱبْتَغَوُا۟"),           # ...and on the plural wāw
    ("نَظُنُّ", "نَّظُنُّ"),               # first letter doubled by the preceding nūn (idghām)
    ("رَحِمَ", "رَّحِمَ"),
    ("اِتَّخَذْتَ", "تَّخَذْتَ"),           # waṣl dropped after لَ, then assimilation (18:77)
    ("اِسْتَغْفَرْتَ", "سْتَغْفَرْتَ"),       # waṣl absorbed by the question hamza (63:6)
    ("اِئْتِ", "أْتِ"),                   # waṣl dropped after فَ, hamza seated on alif
    ("اُؤْمُرْ", "أْمُرْ"),
    ("وَجَدْتُ", "وَجَدتُّ"),              # د assimilated into the suffix ت
    ("أَرَدْتُمْ", "أَرَدتُّمْ"),
])
def test_marks_that_only_belong_to_a_word_join_are_not_a_disagreement(generated, attested):
    assert agrees_across_join(generated, attested)


@pytest.mark.parametrize("generated, attested", [
    ("مُتْتُ", "مِتُّ"),                  # a wrong vowel and a missing assimilation
    ("تَتَذَكَّرُونَ", "تَذَكَّرُونَ"),       # a whole syllable
    ("تَسْتَطِيعُ", "تَسْطِع"),            # a letter
    ("كَانَا", "كَانَتَا"),
    ("كَتَبْتَ", "كَتَبْتُ"),              # a final vowel that is not a helping vowel
    ("فَعَلَ", "فُعِلَ"),
])
def test_a_genuine_difference_still_disagrees_across_a_join(generated, attested):
    assert not agrees_across_join(generated, attested)


def test_a_join_spelling_of_the_quran_reconciles_as_attested():
    cells = reconcile([{"imperative": {"anta": "ذَرْ"}}], {("imperative", "anta"): "ذَرِ"})

    assert cells[0].source == "attested" and cells[0].arabic == "ذَرِ"
    assert cells[0].alternatives == ()
