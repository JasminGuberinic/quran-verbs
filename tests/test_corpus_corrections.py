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
from fil.examples import spelling_key
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
    {"غني_1": {"69:28:2": {"why": "w", "form": 1}}},                        # refiled to itself
    {"غني_1": {"69:28:2": {"why": "w", "form": 11}}},                       # no such form
    {"أتي_4": {"7:190:2": {"why": "w", "mood": "IND"}}},                     # a mood without its tense
    {"أتي_4": {"7:190:2": {"why": "w", "voice": "middle"}}},                 # no such voice
    {"أتي_4": {"7:190:2": {"why": "w", "tense": "past", "person": "he"}}},   # no such person
    {"أتي_4": {"7:190:2": {"why": "w", "tense": "past", "person": "1MS"}}},  # a first person has no gender
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
    for correction in (*corrections.misattributions, *corrections.tense_corrections,
                       *corrections.form_corrections):
        assert (correction.location, correction.root, correction.form) in filed


def test_every_tense_correction_changes_what_the_corpus_says():
    # A correction that restates the corpus's own tense, person or voice is stale and documents nothing.
    with QAC_MORPHOLOGY.open(encoding="utf-8") as lines:
        filed = {(f"{o.surah}:{o.ayah}:{o.word}", o.root, o.form): o for o in iter_verb_occurrences(iter_segments(lines))}
    for correction in service.corpus_corrections().tense_corrections:
        occurrence = filed[(correction.location, correction.root, correction.form)]
        changes = [
            correction.tense is not None and (occurrence.tense, occurrence.mood) != (correction.tense, correction.mood),
            correction.person is not None and (occurrence.person, occurrence.gender, occurrence.number) != correction.person,
            correction.is_passive is not None and occurrence.passive != correction.is_passive,
        ]
        assert any(changes), correction.location


_GAVE = "7:190:2:1\tءَاتَىٰ\tV\tIMPF|VF:4|ROOT:أتي|LEM:آتَى|1S|MOOD:IND"
_SHOWED = "4:105:10:1\tأَرَىٰ\tV\tIMPF|VF:1|ROOT:رأي|LEM:رَأَى|1S|MOOD:SUBJ"


def test_a_mis_tagged_person_is_corrected_with_its_tense():
    # فَلَمَّآ ءَاتَىٰهُمَا (7:190) "when He gave them": the corpus reads the letters as "I give".
    corrections = parse_corrections({"أتي_4": {"7:190:2": {"tense": "past", "person": "3MS", "why": "he gave"}}})
    (occurrence,) = apply_corrections(map(parse_line, (_GAVE,)), corrections)

    assert (occurrence.tense, occurrence.mood, occurrence.person, occurrence.gender, occurrence.number) \
        == ("past", None, 3, "M", "S")


def test_a_word_wrong_in_form_tense_and_person_is_corrected_in_all_three():
    # بِمَآ أَرَىٰكَ ٱللَّهُ (4:105) "by what Allah has shown you": Form IV past, tagged Form I "I see".
    corrections = parse_corrections(
        {"رأي_1": {"4:105:10": {"form": 4, "tense": "past", "person": "3MS", "why": "he showed"}}})
    (occurrence,) = apply_corrections(map(parse_line, (_SHOWED,)), corrections)

    assert (occurrence.form, occurrence.tense, occurrence.person, occurrence.number) == (4, "past", 3, "S")


_CALLS_ME = "2:186:11:1\tدَعَا\tV\tPERF|VF:1|ROOT:دعو|LEM:دَعا|2MS"
_DENY = "29:18:2:1\tتُكَذِّبُ\tV\tIMPF|VF:2|PASS|ROOT:كذب|LEM:كَذَّبَ|2MP|MOOD:SUBJ"


def test_a_person_or_a_voice_is_corrected_alone():
    # إِذَا دَعَانِ (2:186) "when he calls Me", tagged "you"; وَإِن تُكَذِّبُوا۟ (29:18) "if you deny", tagged passive.
    corrections = parse_corrections({"دعو_1": {"2:186:11": {"person": "3MS", "why": "he calls"}},
                                     "كذب_2": {"29:18:2": {"voice": "active", "why": "you deny"}}})
    calls, deny = apply_corrections(map(parse_line, (_CALLS_ME, _DENY)), corrections)

    assert (calls.tense, calls.person, calls.gender, calls.number) == ("past", 3, "M", "S")
    assert (deny.tense, deny.passive, deny.person) == ("present", False, 2)


_AVAILED = "69:28:2:1\tأَغْنَىٰ\tV\tPERF|VF:1|ROOT:غني|LEM:أَغْنَى|3MS"
_REFILED = parse_corrections({"غني_1": {"69:28:2": {"form": 4, "why": "أَغْنَى is Form IV"}}})


def test_a_misformed_occurrence_moves_to_its_true_form():
    (occurrence,) = apply_corrections(map(parse_line, (_AVAILED,)), _REFILED)

    assert (occurrence.root, occurrence.form, occurrence.tense) == ("غني", 4, "past")
    assert build_oracle([occurrence])[("غني", 4)] == {("past", "huwa"): "أَغْنَىٰ"}


def test_to_dwell_no_longer_carries_the_form_iv_to_avail():
    dwell, avail = service.get_verb("غني", 1), service.get_verb("غني", 4)

    assert dwell.lemma == "غَنِيَ" and "69:28" not in dwell.ayat
    assert "69:28" in avail.ayat and "9:74" not in dwell.ayat


def test_come_is_the_imperative_of_the_form_vi_to_be_exalted():
    # The corpus tags every تَعَالَ / تَعَالَوْا / تَعَالَيْنَ "come!" VF:4; refiled, the one
    # Form VI card carries both senses and there is no Form IV card left.
    exalted = service.get_verb("علو", 6)
    spellings = {(cell.tense, cell.pronoun): set(map(spelling_key, cell.spellings)) for cell in exalted.cells}

    assert ("علو", 4) not in {(verb.root, verb.form) for verb in service.list_verbs()}
    assert exalted.lemma == "تَعالَى" and {"3:61", "33:28", "6:100"} <= set(exalted.ayat)
    assert spelling_key("تَعَالَ") in spellings[("imperative", "anta")]
    assert spelling_key("تَعَالَوْا") in spellings[("imperative", "antum")]
    assert spelling_key("تَعَالَيْنَ") in spellings[("imperative", "antunna")]


def test_to_show_the_way_no_longer_claims_lowering_by_deception():
    # فَدَلَّىٰهُمَا (7:22) is دَلَّى "to let down" (root دلو); without it, دَلَّ يَدُلُّ is
    # generated from its documented present vowel.
    guide = service.get_verb("دلل", 1)
    table = {(cell.tense, cell.pronoun): spelling_key(cell.arabic) for cell in guide.cells}

    assert "7:22" not in guide.ayat
    assert (table[("past", "huwa")], table[("present", "huwa")]) == (spelling_key("دَلَّ"), spelling_key("يَدُلُّ"))


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


def test_every_ayah_verb_gloss_is_a_verb_a_card_shows():
    # A correction that moves a word off its verb or out of its tense changes which ayat
    # the cards show: a gloss no card highlights is stale. (A shown verb without one shows
    # its grammar until it is glossed.)
    with QAC_MORPHOLOGY.open(encoding="utf-8") as lines:
        ayat = ayat_of(words_of(iter_segments(lines), service.corpus_corrections()))
    verbs = [(meaning.root, meaning.form) for meaning in meanings.load()]
    uses = service.form_occurrences()
    shown = {f"{word.surah}:{word.ayah}:{word.number}"
             for verb in verbs for example in example_ayat(ayat, verb, uses[verb])
             for word in example.words if word.carries(verb)}
    glossed = {key for key in json.loads(AYAH_VERB_GLOSSES_JSON.read_text(encoding="utf-8"))
               if not key.startswith("_")}

    assert sorted(glossed - shown) == []
