"""Tests for documented corpus corrections — words the corpus files under the wrong verb."""

import pytest

from fil import service
from fil.corpus.catalog import build_catalog
from fil.corpus.corrections import (
    NO_CORRECTIONS,
    CorrectionFormatError,
    parse_corrections,
    without_misattributed,
)
from fil.corpus.oracle import build_oracle
from fil.corpus.parse import iter_segments, iter_verb_occurrences, parse_line
from fil.resources import QAC_MORPHOLOGY

_WEARS_OUT = "20:120:13:1\tيَبْلَىٰ\tV\tIMPF|VF:1|ROOT:بلو|LEM:بَلَوْ|3MS|MOOD:IND"
_TESTS = "16:92:22:1\tيَبْلُو\tV\tIMPF|VF:1|ROOT:بلو|LEM:بَلَوْ|3MS|MOOD:IND"
_CORRECTIONS = parse_corrections({"بلو_1": {"20:120:13": {"why": "يَبْلَىٰ is بَلِيَ, to wear out"}}})


def test_a_misfiled_occurrence_is_dropped_from_counts_ayat_and_attested_cells():
    occurrences = list(without_misattributed(map(parse_line, (_WEARS_OUT, _TESTS)), _CORRECTIONS))

    (entry,) = build_catalog(occurrences)
    assert (entry.occurrence_count, entry.ayat) == (1, ("16:92",))
    assert build_oracle(occurrences)[("بلو", 1)][("present", "huwa")] == "يَبْلُو"


def test_a_correction_only_removes_the_named_verb_at_the_named_word():
    elsewhere = "20:121:13:1\tيَبْلَىٰ\tV\tIMPF|VF:1|ROOT:بلو|LEM:بَلَوْ|3MS|MOOD:IND"
    other_verb = "20:120:13:1\tيَبْلَىٰ\tV\tIMPF|VF:4|ROOT:بلو|LEM:بَلَوْ|3MS|MOOD:IND"
    kept = list(without_misattributed(map(parse_line, (elsewhere, other_verb)), _CORRECTIONS))

    assert len(kept) == 2


def test_no_corrections_keeps_everything():
    assert len(list(without_misattributed(map(parse_line, (_WEARS_OUT,)), NO_CORRECTIONS))) == 1


@pytest.mark.parametrize("raw", [
    {"بلو": {"20:120:13": {"why": "w"}}},          # no form
    {"بلو_1": {"20:120": {"why": "w"}}},           # not a word location
    {"بلو_1": {"20:120:13": {"why": "  "}}},       # undocumented
])
def test_a_malformed_or_undocumented_correction_fails_fast(raw):
    with pytest.raises(CorrectionFormatError):
        parse_corrections(raw)


def test_every_documented_correction_names_a_real_occurrence():
    # A stale entry (wrong location, root or form) would silently correct nothing.
    with QAC_MORPHOLOGY.open(encoding="utf-8") as lines:
        filed = {(f"{o.surah}:{o.ayah}:{o.word}", o.root, o.form)
                 for o in iter_verb_occurrences(iter_segments(lines))}
    for misattribution in service.corpus_corrections().misattributions:
        assert (misattribution.location, misattribution.root, misattribution.form) in filed


def test_to_test_no_longer_claims_the_ayah_about_wearing_out():
    detail = service.get_verb("بلو", 1)

    assert "20:120" not in detail.ayat
    with QAC_MORPHOLOGY.open(encoding="utf-8") as lines:
        surfaces = {o.surface for o in service.verb_occurrences(lines) if (o.root, o.form) == ("بلو", 1)}
    assert "يَبْلَىٰ" not in surfaces
