"""Tests for the Quranic word bank (pure — hand-built segments, no corpus file)."""

from fil.corpus.parse import Segment
from fil.vocabulary import build_vocabulary


def _segment(surface: str, pos: str, *features: str, word: int = 1) -> Segment:
    return Segment(surah=1, ayah=1, word=word, index=1, surface=surface, pos=pos,
                   features=features)


def test_a_word_is_aggregated_over_its_attested_spellings():
    entries = build_vocabulary([
        _segment("يَوْمَ", "N", "ROOT:يوم", "LEM:يَوْم", "M", "ACC"),
        _segment("يَوْمِ", "N", "ROOT:يوم", "LEM:يَوْم", "M", "GEN"),
        _segment("يَوْمَ", "N", "ROOT:يوم", "LEM:يَوْم", "M", "ACC"),
    ])

    assert len(entries) == 1
    word = entries[0]
    assert word.lemma == "يَوْم" and word.root == "يوم" and word.word_class == "noun"
    assert word.occurrence_count == 3
    assert word.surfaces == ("يَوْمَ", "يَوْمِ")  # most frequent spelling first


def test_rootless_function_words_are_not_vocabulary():
    # The corpus files these under the noun tag too, but a word with no root is not
    # something a sentence can be built out of.
    entries = build_vocabulary([
        _segment("هُوَ", "N", "PRON", "3MS"),
        _segment("إِذَا", "N", "T", "LEM:إِذا"),
        _segment("مَن", "N", "REL", "LEM:مَن"),
    ])

    assert entries == []


def test_verbs_particles_and_clitics_are_left_out():
    entries = build_vocabulary([
        _segment("كَتَبَ", "V", "PERF", "ROOT:كتب", "LEM:كَتَبَ", "3MS"),
        _segment("بِ", "P", "P", "PREF", "LEM:ب"),
        _segment("هُمْ", "N", "PRON", "SUFF", "3MP"),
    ])

    assert entries == []


def test_adjectives_and_names_are_classed_apart_from_nouns():
    entries = build_vocabulary([
        _segment("رَّحِيمُ", "N", "ROOT:رحم", "LEM:رَحِيم", "MS", "ADJ"),
        _segment("ٱللَّهِ", "N", "PN", "ROOT:أله", "LEM:اللَّه", "GEN"),
        _segment("رَبِّ", "N", "ROOT:ربب", "LEM:رَبّ", "M", "GEN"),
    ])

    assert {entry.lemma: entry.word_class for entry in entries} == {
        "رَحِيم": "adjective",
        "اللَّه": "proper_noun",
        "رَبّ": "noun",
    }


def test_the_bank_is_ordered_by_frequency():
    entries = build_vocabulary(
        [_segment("رَبِّ", "N", "ROOT:ربب", "LEM:رَبّ")] * 3
        + [_segment("يَوْمَ", "N", "ROOT:يوم", "LEM:يَوْم")] * 5
    )

    assert [entry.lemma for entry in entries] == ["يَوْم", "رَبّ"]
