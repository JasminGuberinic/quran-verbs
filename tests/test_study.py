"""Tests for the study selection — pure decisions over synthetic corpus segments."""

from fil.corpus.parse import parse_segment
from fil.study import (
    ayat_of,
    derived_nouns,
    example_ayat,
    standalone_locations,
    words_of,
)

_SAY = ("قول", 1)


def _segments(*lines: str):
    return [parse_segment(line) for line in lines]


def _ayah(surah: int, ayah: int, *words: tuple[str, str, str]):
    """Lines for one ayah: each word is (surface, pos, features)."""
    return [
        f"{surah}:{ayah}:{number}:1\t{surface}\t{pos}\t{features}"
        for number, (surface, pos, features) in enumerate(words, 1)
    ]


_QALA = ("قَالَ", "V", "PERF|VF:1|ROOT:قول|LEM:قالَ|3MS")
_YAQULU = ("يَقُولُ", "V", "IMPF|VF:1|ROOT:قول|LEM:قالَ|3MS|MOOD:IND")
_QULA = ("قِيلَ", "V", "PERF|PASS|VF:1|ROOT:قول|LEM:قالَ|3MS")
_NOUN = ("ٱلْحَقَّ", "N", "ROOT:حقق|LEM:حَقّ|M|ACC")


def _corpus():
    lines = [
        *_ayah(1, 1, _QALA, _NOUN, _NOUN, _NOUN, _NOUN),        # past, 5 words
        *_ayah(1, 2, _QALA, _NOUN, _NOUN),                      # past, 3 words — shortest
        *_ayah(1, 3, _YAQULU, _NOUN, _NOUN, _NOUN),             # present
        *_ayah(1, 4, _QULA, _NOUN, _NOUN),                      # passive only
    ]
    return _segments(*lines)


def test_words_join_segments_and_carry_only_active_verbs():
    words = words_of(_corpus())

    first = words[0]
    assert first.text == "قَالَ" and first.carries(_SAY, "past")
    passive = next(word for word in words if word.text == "قِيلَ")
    assert not passive.carries(_SAY)


def test_one_shortest_ayah_per_tense():
    chosen = example_ayat(ayat_of(words_of(_corpus())), _SAY)

    assert [(example.ref, example.tense) for example in chosen] == [("1:2", "past"), ("1:3", "present")]


def test_a_passive_ayah_is_never_offered():
    # Passive "it was said" looks like the verb but teaches the wrong direction.
    chosen = example_ayat(ayat_of(words_of(_corpus())), _SAY)

    assert "1:4" not in {example.ref for example in chosen}


def test_a_form_is_located_only_where_it_stands_alone():
    words = words_of(_segments(
        "2:1:1:1\tفَ\tCONJ\tCONJ|PREF|LEM:ف",
        "2:1:1:2\tقَالَ\tV\tPERF|VF:1|ROOT:قول|LEM:قالَ|3MS",
        "2:2:1:1\tقَالَ\tV\tPERF|VF:1|ROOT:قول|LEM:قالَ|3MS",
    ))

    assert standalone_locations(words)["قَالَ"] == (2, 2, 1)


def test_derived_nouns_come_from_corpus_tags():
    nouns = derived_nouns(_segments(
        "3:1:1:1\tقَآئِلٌ\tN\tACT_PCPL|VF:1|ROOT:قول|LEM:قائِل|M|NOM",
        "3:1:2:1\tقَوْلًا\tN\tVN|VF:1|ROOT:قول|LEM:قَوْل|M|ACC",
        "3:1:3:1\tقَوْلُ\tN\tVN|VF:1|ROOT:قول|LEM:قَوْل|M|NOM",
    ))

    assert nouns[_SAY]["participle"].lemma == "قائِل"
    assert (nouns[_SAY]["verbal_noun"].lemma, nouns[_SAY]["verbal_noun"].count) == ("قَوْل", 2)
