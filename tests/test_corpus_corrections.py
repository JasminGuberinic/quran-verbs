"""Tests for documented corpus corrections — words the corpus files under the wrong verb."""

import json

import pytest

from fil import meanings, service
from fil.corpus.catalog import build_catalog
from fil.corpus.corrections import (
    NO_CORRECTIONS,
    CorrectionFormatError,
    parse_corrections,
    apply_corrections,
)
from fil.corpus.oracle import build_oracle
from fil.corpus.parse import iter_segments, iter_verb_occurrences, parse_line
from fil.resources import AYAH_VERB_GLOSSES_JSON, QAC_MORPHOLOGY
from fil.study import ayat_of, example_ayat, words_of

_WEARS_OUT = "20:120:13:1\tيَبْلَىٰ\tV\tIMPF|VF:1|ROOT:بلو|LEM:بَلَوْ|3MS|MOOD:IND"
_TESTS = "16:92:22:1\tيَبْلُو\tV\tIMPF|VF:1|ROOT:بلو|LEM:بَلَوْ|3MS|MOOD:IND"
_CORRECTIONS = parse_corrections({"بلو_1": {"20:120:13": {"why": "يَبْلَىٰ is بَلِيَ, to wear out"}}})


def test_a_misfiled_occurrence_is_dropped_from_counts_ayat_and_attested_cells():
    occurrences = list(apply_corrections(map(parse_line, (_WEARS_OUT, _TESTS)), _CORRECTIONS))

    (entry,) = build_catalog(occurrences)
    assert (entry.occurrence_count, entry.ayat) == (1, ("16:92",))
    assert build_oracle(occurrences)[("بلو", 1)][("present", "huwa")] == "يَبْلُو"


def test_a_correction_only_removes_the_named_verb_at_the_named_word():
    elsewhere = "20:121:13:1\tيَبْلَىٰ\tV\tIMPF|VF:1|ROOT:بلو|LEM:بَلَوْ|3MS|MOOD:IND"
    other_verb = "20:120:13:1\tيَبْلَىٰ\tV\tIMPF|VF:4|ROOT:بلو|LEM:بَلَوْ|3MS|MOOD:IND"
    kept = list(apply_corrections(map(parse_line, (elsewhere, other_verb)), _CORRECTIONS))

    assert len(kept) == 2


def test_no_corrections_keeps_everything():
    assert len(list(apply_corrections(map(parse_line, (_WEARS_OUT,)), NO_CORRECTIONS))) == 1


_STRIVING = "79:22:3:1\tيَسْعَىٰ\tV\tPERF|VF:1|ROOT:سعي|LEM:سَعَى|3MS"
_RETENSED = parse_corrections({"سعي_1": {"79:22:3": {"tense": "present", "mood": "IND", "why": "a present"}}})


def test_a_mis_tensed_occurrence_is_kept_with_its_true_tense_and_mood():
    (occurrence,) = apply_corrections(map(parse_line, (_STRIVING,)), _RETENSED)

    assert (occurrence.tense, occurrence.mood, occurrence.surface) == ("present", "IND", "يَسْعَىٰ")
    assert build_oracle([occurrence])[("سعي", 1)] == {("present", "huwa"): "يَسْعَىٰ"}


@pytest.mark.parametrize("raw", [
    {"بلو": {"20:120:13": {"why": "w"}}},          # no form
    {"بلو_1": {"20:120": {"why": "w"}}},           # not a word location
    {"بلو_1": {"20:120:13": {"why": "  "}}},       # undocumented
    {"سعي_1": {"79:22:3": {"why": "w", "tense": "future"}}},                 # no such tense
    {"سعي_1": {"79:22:3": {"why": "w", "tense": "present"}}},                # a present without its mood
    {"سعي_1": {"79:22:3": {"why": "w", "tense": "past", "mood": "IND"}}},    # a mood on a past
])
def test_a_malformed_or_undocumented_correction_fails_fast(raw):
    with pytest.raises(CorrectionFormatError):
        parse_corrections(raw)


def test_every_documented_correction_names_a_real_occurrence():
    # A stale entry (wrong location, root or form) would silently correct nothing.
    with QAC_MORPHOLOGY.open(encoding="utf-8") as lines:
        filed = {(f"{o.surah}:{o.ayah}:{o.word}", o.root, o.form)
                 for o in iter_verb_occurrences(iter_segments(lines))}
    corrections = service.corpus_corrections()
    for correction in (*corrections.misattributions, *corrections.tense_corrections):
        assert (correction.location, correction.root, correction.form) in filed


def test_every_tense_correction_changes_what_the_corpus_says():
    # A correction that restates the corpus's own tense is stale and documents nothing.
    with QAC_MORPHOLOGY.open(encoding="utf-8") as lines:
        filed = {(f"{o.surah}:{o.ayah}:{o.word}", o.root, o.form): (o.tense, o.mood)
                 for o in iter_verb_occurrences(iter_segments(lines))}
    for correction in service.corpus_corrections().tense_corrections:
        assert filed[(correction.location, correction.root, correction.form)] != (correction.tense, correction.mood)


def test_he_strives_in_79_22_counts_as_a_present_not_a_past():
    with QAC_MORPHOLOGY.open(encoding="utf-8") as lines:
        (striving,) = (o for o in service.verb_occurrences(lines) if (o.surah, o.ayah, o.word) == (79, 22, 3))

    assert (striving.root, striving.tense, striving.mood) == ("سعي", "present", "IND")


def test_to_test_no_longer_claims_the_ayah_about_wearing_out():
    detail = service.get_verb("بلو", 1)

    assert "20:120" not in detail.ayat
    with QAC_MORPHOLOGY.open(encoding="utf-8") as lines:
        surfaces = {o.surface for o in service.verb_occurrences(lines) if (o.root, o.form) == ("بلو", 1)}
    assert "يَبْلَىٰ" not in surfaces


def test_every_ayah_verb_gloss_is_shown_on_some_card():
    # A gloss no card highlights is stale — left behind when a correction moved the word
    # off its verb or out of its tense — and would be translated into every language for nothing.
    with QAC_MORPHOLOGY.open(encoding="utf-8") as lines:
        ayat = ayat_of(words_of(iter_segments(lines), service.corpus_corrections()))
    verbs = [(meaning.root, meaning.form) for meaning in meanings.load()]
    shown = {f"{word.surah}:{word.ayah}:{word.number}"
             for verb in verbs for example in example_ayat(ayat, verb)
             for word in example.words if word.carries(verb)}
    glossed = {key for key in json.loads(AYAH_VERB_GLOSSES_JSON.read_text(encoding="utf-8"))
               if not key.startswith("_")}

    assert sorted(glossed - shown) == []
