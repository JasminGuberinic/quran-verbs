"""Tests for the study selection — pure decisions over synthetic corpus segments."""

from fil.attested_forms import form_occurrences, word_texts
from fil.corpus.corrections import NO_CORRECTIONS, parse_corrections
from fil.corpus.parse import iter_verb_occurrences, parse_segment
from fil.study import (
    MAX_EXAMPLES,
    ayat_of,
    derived_nouns,
    example_ayat,
    recitation_index,
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
    words = words_of(_corpus(), NO_CORRECTIONS)

    first = words[0]
    assert first.text == "قَالَ" and first.carries(_SAY, "past")
    passive = next(word for word in words if word.text == "قِيلَ")
    assert not passive.carries(_SAY)


def _examples(segments, verb=_SAY):
    uses = form_occurrences(iter_verb_occurrences(iter(segments)), word_texts(segments)).get(verb, ())
    return example_ayat(ayat_of(words_of(segments, NO_CORRECTIONS)), verb, uses)


def test_one_shortest_ayah_per_tense():
    chosen = _examples(_corpus())

    assert [(example.ref, example.category) for example in chosen] == [("1:2", ("past", "huwa")),
                                                                       ("1:3", ("present", "huwa"))]


def test_a_passive_ayah_is_never_offered():
    # Passive "it was said" looks like the verb but teaches the wrong direction.
    chosen = _examples(_corpus())

    assert "1:4" not in {example.ref for example in chosen}


_QALU = ("قَالُوا۟", "V", "PERF|VF:1|ROOT:قول|LEM:قالَ|3MP")
_QULTU = ("قُلْتُ", "V", "PERF|VF:1|ROOT:قول|LEM:قالَ|1S")
_YAQULUNA = ("يَقُولُونَ", "V", "IMPF|VF:1|ROOT:قول|LEM:قالَ|3MP|MOOD:IND")
_QUL = ("قُلْ", "V", "IMPV|VF:1|ROOT:قول|LEM:قالَ|2MS")


def _many_forms():
    return _segments(
        *_ayah(2, 1, _QULTU, _NOUN, _NOUN),                     # past · I — the shortest past
        *_ayah(2, 2, _QALA, _NOUN, _NOUN, _NOUN),               # past · he, three times over
        *_ayah(2, 3, _QALA, _NOUN, _NOUN, _NOUN, _NOUN),
        *_ayah(2, 4, _QALA, _NOUN, _NOUN, _NOUN, _NOUN, _NOUN),
        *_ayah(2, 5, _QALU, _NOUN, _NOUN, _NOUN, _NOUN),        # past · they, twice
        *_ayah(2, 6, _QALU, _NOUN, _NOUN, _NOUN),
        *_ayah(2, 7, _YAQULU, _NOUN, _NOUN, _NOUN),             # present · he
        *_ayah(2, 8, _YAQULUNA, _NOUN, _NOUN, _NOUN, _NOUN),    # present · they
        *_ayah(2, 9, _QUL, _NOUN, _NOUN, _NOUN),                # imperative · you
        *_ayah(2, 10, _QALA, *[_NOUN] * 12),                     # too long to show
        *_ayah(2, 11, _QULA, _NOUN, _NOUN),                     # passive
    )


def test_each_example_shows_another_form_the_commonest_first():
    chosen = _examples(_many_forms())

    assert [(example.ref, example.category) for example in chosen] == [
        ("2:2", ("past", "huwa")),       # 4 uses (one in an ayah too long to show)
        ("2:6", ("past", "hum")),        # 2 uses, its shorter ayah
        ("2:1", ("past", "ana")),        # 1 use each: the Quran's order breaks the tie
        ("2:7", ("present", "huwa")),
        ("2:8", ("present", "hum")),
        ("2:9", ("imperative", "anta")),
    ]


def test_the_ayah_chosen_for_each_tense_always_stays():
    # Its verb is already glossed and translated: a commoner form gets another ayah instead.
    chosen = _examples(_many_forms())

    assert {"2:1", "2:7", "2:9"} <= {example.ref for example in chosen}


def test_never_more_than_the_maximum_and_never_one_ayah_twice():
    extra = [_ayah(3, n, ("قُلْنَا", "V", f"PERF|VF:1|ROOT:قول|LEM:قالَ|{person}"), _NOUN, _NOUN)
             for n, person in enumerate(("1P", "3FS", "2MP", "3FP", "2FS"), 1)]
    chosen = _examples([*_many_forms(), *_segments(*[line for ayah in extra for line in ayah])])

    assert len(chosen) == MAX_EXAMPLES
    assert len({example.ref for example in chosen}) == MAX_EXAMPLES
    assert len({example.category for example in chosen}) == MAX_EXAMPLES


def test_the_choice_is_the_same_every_time():
    assert _examples(_many_forms()) == _examples(_many_forms())


def test_a_form_is_located_only_where_it_stands_alone():
    words = words_of(_segments(
        "2:1:1:1\tفَ\tCONJ\tCONJ|PREF|LEM:ف",
        "2:1:1:2\tقَالَ\tV\tPERF|VF:1|ROOT:قول|LEM:قالَ|3MS",
        "2:2:1:1\tقَالَ\tV\tPERF|VF:1|ROOT:قول|LEM:قالَ|3MS",
    ), NO_CORRECTIONS)

    assert standalone_locations(words)["قَالَ"] == (2, 2, 1)


def test_derived_nouns_come_from_corpus_tags():
    nouns = derived_nouns(_segments(
        "3:1:1:1\tقَآئِلٌ\tN\tACT_PCPL|VF:1|ROOT:قول|LEM:قائِل|M|NOM",
        "3:1:2:1\tقَوْلًا\tN\tVN|VF:1|ROOT:قول|LEM:قَوْل|M|ACC",
        "3:1:3:1\tقَوْلُ\tN\tVN|VF:1|ROOT:قول|LEM:قَوْل|M|NOM",
    ))

    assert nouns[_SAY]["participle"].lemma == "قائِل"
    assert (nouns[_SAY]["verbal_noun"].lemma, nouns[_SAY]["verbal_noun"].count) == ("قَوْل", 2)


def test_a_form_heard_only_behind_a_clitic_is_offered_as_the_whole_word():
    words = words_of(_segments(
        "4:1:1:1\tفَ\tCONJ\tCONJ|PREF|LEM:ف",
        "4:1:1:2\tٱعْلَمْ\tV\tIMPV|VF:1|ROOT:علم|LEM:عَلِمَ|2MS",
        "4:2:1:1\tقَالَ\tV\tPERF|VF:1|ROOT:قول|LEM:قالَ|3MS",
    ), NO_CORRECTIONS)

    index = recitation_index(words)

    assert index["ٱعْلَمْ"].text == "فَٱعْلَمْ"       # what the learner will hear
    assert index["قَالَ"].location == (4, 2, 1)       # alone, exactly as written


def test_a_form_never_recited_has_no_recitation():
    assert "يَقُلْنَ" not in recitation_index(words_of(_corpus(), NO_CORRECTIONS))


def test_a_word_the_corpus_misfiles_is_not_an_example_of_that_verb():
    # 20:120 يَبْلَىٰ "wears out" (بَلِيَ) is filed under بلو form I, "to test".
    segments = _segments("20:120:13:1\tيَبْلَىٰ\tV\tIMPF|VF:1|ROOT:بلو|LEM:بَلَوْ|3MS|MOOD:IND")
    corrections = parse_corrections({"بلو_1": {"20:120:13": {"why": "it is بَلِيَ"}}})

    tagged = words_of(segments, NO_CORRECTIONS)
    corrected = words_of(segments, corrections)

    assert tagged[0].carries(("بلو", 1), "present")
    assert not corrected[0].carries(("بلو", 1), "present")
