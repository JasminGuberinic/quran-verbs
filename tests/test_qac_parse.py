"""Tests for QAC morphology parsing and verb-catalogue aggregation."""

from fil.corpus.catalog import build_catalog
from fil.corpus.parse import iter_segments, iter_verb_occurrences, parse_line


def test_reconstructs_full_form_from_stem_plus_subject_suffix():
    # QAC stores the 3MP subject pronoun (وا۟) as its own segment; the full
    # conjugated form is the stem + that suffix.
    lines = [
        "2:6:3:1\tكَفَرُ\tV\tPERF|VF:1|ROOT:كفر|LEM:كَفَرَ|3MP",
        "2:6:3:2\tوا۟\tN\tPRON|SUFF|3MP",
    ]
    occurrences = list(iter_verb_occurrences(iter_segments(lines)))
    assert len(occurrences) == 1
    assert occurrences[0].surface == "كَفَرُوا۟"


def test_does_not_absorb_a_mismatched_object_pronoun():
    # An object pronoun (different PGN than the verb) must NOT be stitched on.
    lines = [
        "1:7:3:1\tأَنعَمْ\tV\tPERF|VF:4|ROOT:نعم|LEM:أَنعَمَ|2MS",
        "1:7:3:2\tتَ\tN\tPRON|SUFF|2MS",   # subject (matches) → kept
        "1:7:4:1\tعَلَي\tN\tP",
        "1:7:4:2\tهِمْ\tN\tPRON|SUFF|3MP",  # object (different word anyway)
    ]
    occurrences = list(iter_verb_occurrences(iter_segments(lines)))
    assert occurrences[0].surface == "أَنعَمْتَ"  # stem + matching 2MS subject only


def test_third_masc_singular_does_not_absorb_a_matching_object_pronoun():
    # naṣara-hu: verb 3MS + object 3MS (same PGN). 3MS has no subject suffix, so
    # the object must NOT be absorbed, and the occurrence is not a clean citation.
    lines = [
        "3:13:5:1\tنَصَرَ\tV\tPERF|VF:1|ROOT:نصر|LEM:نَصَرَ|3MS",
        "3:13:5:2\tهُ\tN\tPRON|SUFF|3MS",
    ]
    occ = list(iter_verb_occurrences(iter_segments(lines)))[0]
    assert occ.surface == "نَصَرَ"   # object not absorbed
    assert occ.clean is False        # excluded from the citation oracle


def test_parses_present_active_verb():
    occ = parse_line("1:5:2:1\tنَعْبُدُ\tV\tIMPF|VF:1|ROOT:عبد|LEM:عَبَدَ|1P|MOOD:IND")
    assert occ is not None
    assert occ.tense == "present"
    assert occ.root == "عبد"
    assert occ.form == 1
    assert (occ.person, occ.gender, occ.number) == (1, None, "P")
    assert occ.mood == "IND"
    assert occ.passive is False
    assert occ.ayah_ref == "1:5"


def test_parses_passive_past_verb():
    occ = parse_line("2:4:4:1\tأُنزِلَ\tV\tPERF|VF:4|PASS|ROOT:نزل|LEM:أَنزَلَ|3MS")
    assert occ is not None
    assert occ.tense == "past"
    assert occ.passive is True
    assert occ.form == 4
    assert (occ.person, occ.gender, occ.number) == (3, "M", "S")


def test_ignores_non_verb_segments():
    assert parse_line("1:1:1:1\tبِ\tP\tP|PREF|LEM:ب") is None


def test_catalog_groups_by_root_and_form():
    occurrences = [
        parse_line("2:6:3:1\tكَفَرُوا\tV\tPERF|VF:1|ROOT:كفر|LEM:كَفَرَ|3MP"),
        parse_line("3:10:5:1\tكَفَرَ\tV\tPERF|VF:1|ROOT:كفر|LEM:كَفَرَ|3MS"),
        parse_line("2:3:2:1\tيُؤْمِنُ\tV\tIMPF|VF:4|ROOT:أمن|LEM:آمَنَ|3MP|MOOD:IND"),
    ]
    catalog = build_catalog(occurrences)

    assert len(catalog) == 2  # (كفر, I) and (أمن, IV)
    kafara = next(e for e in catalog if e.root == "كفر")
    assert kafara.form == 1
    assert kafara.occurrence_count == 2
    assert kafara.ayat == ("2:6", "3:10")  # unique, in mushaf order
