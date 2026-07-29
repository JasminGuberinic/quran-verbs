"""Tests for the QAC attested-conjugation oracle."""

from fil.corpus.oracle import build_oracle
from fil.corpus.parse import parse_line


def test_maps_occurrence_to_tense_pronoun_cell():
    occs = [parse_line("2:6:3:1\tكَفَرُوا\tV\tPERF|VF:1|ROOT:كفر|LEM:كَفَرَ|3MP")]
    oracle = build_oracle(occs)
    assert oracle[("كفر", 1)][("past", "hum")] == "كَفَرُوا"


def test_duals_merge_regardless_of_gender():
    occs = [parse_line("2:1:1:1\tفَعَلَا\tV\tPERF|VF:1|ROOT:فعل|LEM:فَعَلَ|3MD")]
    oracle = build_oracle(occs)
    assert ("past", "huma") in oracle[("فعل", 1)]


def test_skips_passive_and_non_indicative_present():
    occs = [
        parse_line("2:4:4:1\tأُنزِلَ\tV\tPERF|VF:4|PASS|ROOT:نزل|LEM:أَنزَلَ|3MS"),
        parse_line("2:6:9:1\tتُنذِرْ\tV\tIMPF|VF:4|ROOT:نذر|LEM:أَنذَرَ|2MS|MOOD:JUS"),
    ]
    # Both are excluded (passive; jussive present) → no teachable cells.
    assert build_oracle(occs) == {}
