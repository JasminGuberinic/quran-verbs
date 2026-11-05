"""The noun pilot: Bosnian declension by rule around stored cells, English by rule, composed
glosses of Quranic forms, the case explanation, and the gate for practice sentences.

Golden values are hand-checked Bosnian and Arabic; the fixtures are the corpus's own lines.
"""

from __future__ import annotations

import pytest

from fil.examples import Example, ExampleWord
from fil.nouns import bosnian, english, explanation, gate, sentence_gate
from fil.nouns.bosnian import BosnianNoun, CannotSay, InvalidBosnianNoun, Phrase, possessive_adjective
from fil.nouns.compose import Composed, NounGlossing, Skipped, compose
from fil.nouns.english import EnglishNoun, EnglishPhrase
from fil.nouns.model import (ACCUSATIVE, CONSTRUCT, DEFINITE, DUAL, GENITIVE, INDEFINITE, MISSING, NOMINATIVE,
                             PLURAL, SINGULAR, Cell, ParadigmCell)
from fil.nouns.selection import skip_reason
from fil.nouns.spelling import spelling_key, standalone
from fil.nouns.studied import NounTable, TableRow
from fil.nouns.table import with_documented
from fil.corpus.nouns import iter_noun_occurrences
from fil.corpus.parse import iter_segments

RUKA = BosnianNoun(
    cells={"sg|N": "ruka", "sg|G": "ruke", "sg|D": "ruci", "sg|A": "ruku", "sg|I": "rukom", "sg|L": "ruci",
           "pl|N": "ruke", "pl|G": "ruku", "pl|D": "rukama", "pl|A": "ruke", "pl|I": "rukama", "pl|L": "rukama",
           "du|N": "dvije ruke", "du|G": "dviju ruku", "du|D": "dvjema rukama", "du|A": "dvije ruke",
           "du|I": "dvjema rukama", "du|L": "dvjema rukama"},
    genders={"sg": "f", "pl": "f"},
    prepositions={"fi": "u", "ala": "na", "bi": "", "min": "iz", "ila": "do", "li": "", "ka": "kao"})
ZEMLJA = BosnianNoun(
    cells={"sg|N": "zemlja", "sg|G": "zemlje", "sg|D": "zemlji", "sg|A": "zemlju", "sg|I": "zemljom", "sg|L": "zemlji"},
    genders={"sg": "f"},
    prepositions={"fi": "na", "ala": "na", "bi": "", "min": "iz", "ila": "do", "li": "", "ka": "kao"})
HAND = NounGlossing(EnglishNoun("hand", "hands"), RUKA, lemma="يَد", main_plural="أَيْدِي")
EARTH = NounGlossing(EnglishNoun("earth", "lands", is_countable=False), ZEMLJA, lemma="أَرْض")



def occurrences(*words: list[str]):
    """Noun occurrences from consecutive QAC words, each a list of "surface POS features"."""
    lines = [f"2:1:{number}:{index}\t" + "\t".join(segment.split(" ", 2))
             for number, word in enumerate(words, 1) for index, segment in enumerate(word, 1)]
    return list(iter_noun_occurrences(iter_segments(iter(lines))))


# ---------------------------------------------------------------- Bosnian

@pytest.mark.parametrize(("possessor", "gender", "number", "case", "expected"), [
    ("3MS", "f", "sg", "L", "njegovoj"), ("3MP", "f", "pl", "I", "njihovim"), ("1S", "m", "sg", "G", "mog"),
    ("1P", "m", "sg", "D", "našem"), ("1P", "n", "sg", "N", "naše"), ("2MS", "f", "sg", "A", "tvoju"),
    ("3MS", "ma", "sg", "A", "njegovog"), ("3MS", "m", "sg", "A", "njegov"), ("3FS", "n", "pl", "N", "njena"),
    ("2MP", "f", "pl", "G", "vaših"), ("1S", "f", "sg", "I", "mojom"),
])
def test_the_possessive_adjective_agrees_with_its_noun(possessor, gender, number, case, expected):
    assert possessive_adjective(possessor, gender, number, case) == expected


@pytest.mark.parametrize(("wanted", "expected"), [
    (Phrase(preposition="fi", possessor="3MS"), "u njegovoj ruci"),
    (Phrase(number="pl", preposition="bi", possessor="3MP"), "njihovim rukama"),
    (Phrase(number="pl", preposition="min", conjunction="i"), "i iz ruku"),
    (Phrase(case="A", possessor="1P"), "našu ruku"),
    (Phrase(number="du", case="N"), "dvije ruke"),
    (Phrase(case="G", oath=True), "tako mi ruke"),
])
def test_a_bosnian_phrase_puts_conjunction_preposition_possessive_and_noun_in_order(wanted, expected):
    assert bosnian.phrase(RUKA, wanted) == expected


def test_s_becomes_sa_before_a_sibilant():
    noun = BosnianNoun({"sg|I": "sinom", "pl|I": "zvijezdama"}, {"sg": "ma"}, {"bi": "s"})
    assert bosnian.phrase(noun, Phrase(preposition="bi")) == "sa sinom"
    assert bosnian.phrase(noun, Phrase(number="pl", preposition="bi")) == "sa zvijezdama"


def test_a_preposition_left_uncomposed_cannot_be_said():
    noun = BosnianNoun(RUKA.cells, RUKA.genders, {**RUKA.prepositions, "bi": "-"})
    with pytest.raises(CannotSay):
        bosnian.phrase(noun, Phrase(preposition="bi"))


def test_a_possessed_dual_is_not_guessed():
    with pytest.raises(CannotSay):
        bosnian.phrase(RUKA, Phrase(number="du", possessor="3MS"))


def test_validation_names_every_problem():
    entry = {"cells": {"sg|N": "ruka", "sg|X": "ruke", "sg|G": "رُكا"}, "genders": {"sg": "q"},
             "prepositions": {"fi": "kroz"}}
    with pytest.raises(InvalidBosnianNoun) as error:
        bosnian.validated({"يَد|يدي": entry}, {"يَد|يدي": ("sg",)})
    message = str(error.value)
    for problem in ("sg|X", "not plain Bosnian", "gender", "kroz", "no choice for", "missing sg|D"):
        assert problem in message


# ---------------------------------------------------------------- English

@pytest.mark.parametrize(("wanted", "expected"), [
    (EnglishPhrase(is_definite=True), "the hand"),
    (EnglishPhrase(), "a hand"),
    (EnglishPhrase(number=PLURAL, preposition="bi", possessor="3MP"), "with their hands"),
    (EnglishPhrase(is_genitive=True, is_definite=True, conjunction="and"), "and of the hand"),
    (EnglishPhrase(is_construct=True), "the hand of"),
    (EnglishPhrase(number=DUAL), "two hands"),
])
def test_an_english_phrase(wanted, expected):
    assert english.phrase(EnglishNoun("hand", "hands"), wanted) == expected


def test_a_mass_noun_takes_no_article():
    assert english.phrase(EnglishNoun("water", "waters", is_countable=False), EnglishPhrase()) == "water"


# ---------------------------------------------------------------- composed glosses of Quranic forms

BI_AYDIHIM = ["بِ P P|PREF|LEM:ب", "أَيْدِي N ROOT:يدي|LEM:يَد|FP|GEN", "هِمْ N PRON|SUFF|3MP"]
FI = ["فِى P P|LEM:فِي"]
AL_ARDI = ["ٱلْ P DET|PREF|LEM:ال", "أَرْضِ N ROOT:أرض|LEM:أَرْض|F|GEN"]
INNA = ["إِنَّ P ACC|LEM:إِنّ|FAM:إِنّ"]
AL_ARDA = ["ٱلْ P DET|PREF|LEM:ال", "أَرْضَ N ROOT:أرض|LEM:أَرْض|F|ACC"]
YA = ["يَٰٓ P VOC|PREF|LEM:يا", "أَرْضُ N ROOT:أرض|LEM:أَرْض|F|NOM"]


def test_a_preposition_attached_and_a_possessor():
    (noun,) = occurrences(BI_AYDIHIM)
    assert compose([noun], HAND) == Composed("with their hands", "njihovim rukama", "I")


def test_the_preposition_standing_before_chooses_the_bosnian_case():
    (noun,) = occurrences(FI, AL_ARDI)
    assert compose([noun], EARTH) == Composed("in the earth", "na zemlji", "L")


def test_a_bare_genitive_is_of():
    (noun,) = occurrences(AL_ARDI)
    assert compose([noun], EARTH) == Composed("of the earth", "zemlje", "G")


def test_an_accusative_after_inna_is_no_object():
    (noun,) = occurrences(INNA, AL_ARDA)
    assert compose([noun], EARTH) == Skipped("accusative after inna")


def test_an_accusative_object_is_composed():
    (noun,) = occurrences(AL_ARDA)
    assert compose([noun], EARTH) == Composed("the earth", "zemlju", "A")


def test_a_vocative_keeps_its_label():
    (noun,) = occurrences(YA)
    assert isinstance(compose([noun], EARTH), Skipped)


def test_two_places_reading_differently_keep_the_label():
    (accusative,) = occurrences(AL_ARDA)
    (after_inna,) = occurrences(INNA, AL_ARDA)
    assert compose([accusative, after_inna], EARTH) == Skipped("readings differ")


def test_a_polysemous_noun_is_never_composed():
    (noun,) = occurrences(AL_ARDA)
    polysemous = NounGlossing(EARTH.english, EARTH.bosnian, lemma="أَرْض", is_polysemous=True)
    assert compose([noun], polysemous) == Skipped("polysemous noun")


def test_a_dual_that_keeps_its_nun_is_indefinite():
    (noun,) = occurrences(["عَيْنَانِ N ROOT:عين|LEM:عَيْن|FD|NOM"])
    assert noun.state == INDEFINITE


# ---------------------------------------------------------------- the gate and the table

def test_a_final_long_alif_carries_no_case_vowel():
    assert gate.problems("الْعَصاُ", Cell(SINGULAR, DEFINITE, NOMINATIVE), "عَصا")
    assert not gate.problems("الْعَصَا", Cell(SINGULAR, DEFINITE, NOMINATIVE), "عَصا")


def test_a_standalone_cell_drops_the_iqlab_mark_of_the_next_word():
    assert standalone("كَافِرٍۭ") == "كَافِرٍ"
    assert standalone("طَيْرًۢا") == "طَيْرًا"


def test_a_documented_cell_must_pass_the_gate_and_never_replaces_the_quran():
    row = TableRow(SINGULAR, SINGULAR, None, (
        ParadigmCell(Cell(SINGULAR, DEFINITE, NOMINATIVE), "ٱلْعَصَا", "attested"),
        ParadigmCell(Cell(SINGULAR, DEFINITE, ACCUSATIVE), None, MISSING)))
    table = NounTable("عَصا|عصو", (row,))
    documented = with_documented(table, {"S|definite|NOM": {"text": "x", "why": "w"},
                                         "S|definite|ACC": {"text": "الْعَصَا", "why": "w"}}, "عَصا")
    assert [found.text for found in documented.rows[0].cells] == ["ٱلْعَصَا", "الْعَصَا"]
    with pytest.raises(ValueError):
        with_documented(table, {"S|definite|ACC": {"text": "الْعَصاُ", "why": "w"}}, "عَصا")


def test_adverbs_quantifiers_and_adjectives_get_no_noun_card():
    from fil.nouns.model import ADJECTIVE, NOUN, NounLemma

    def lemma(text, kind=NOUN):
        return NounLemma(text, "r", kind, None, 1, 1, None, (), 0, (), None)
    assert skip_reason(lemma("كُلّ")) == "quantifier"
    assert skip_reason(lemma("عَلِيم", ADJECTIVE)) == "adjective"
    assert skip_reason(lemma("بَيْت")) is None


def test_a_lemma_is_skipped_whatever_order_its_marks_come_in():
    from fil.nouns.model import NOUN, NounLemma
    shadda_before_fatha = "\u0623\u064e\u0648\u0651\u064e\u0644"  # أَوَّل as the corpus writes it
    assert skip_reason(NounLemma(shadda_before_fatha, "r", NOUN, None, 1, 1, None, (), 0, (), None)) == "adjective-like"


# ---------------------------------------------------------------- the case explanation

@pytest.mark.parametrize(("nominative", "expected"), [
    ("بَيْتٌ", "بَيْتُهُ"), ("شَجَرَةٌ", "شَجَرَتُهُ"), ("مَاءٌ", None), ("كِتَابًا", None),
])
def test_his_is_added_only_to_a_regular_stem(nominative, expected):
    assert explanation.with_his(nominative) == expected


def test_the_explanation_shows_each_case_with_the_noun():
    cells = {(SINGULAR, DEFINITE, NOMINATIVE): "الْأَرْضُ", (SINGULAR, DEFINITE, ACCUSATIVE): "الْأَرْضَ",
             (SINGULAR, DEFINITE, GENITIVE): "الْأَرْضِ", (SINGULAR, INDEFINITE, NOMINATIVE): "أَرْضٌ"}
    idafa = explanation.Idafa("لَوْنُ", "color", "boja")
    found = explanation.examples(cells, EARTH, idafa, ["fi", "ala"], None)
    assert [(example.role, example.arabic, example.bs) for example in found] == [
        ("subject", "الْأَرْضُ", "zemlja"), ("object", "الْأَرْضَ", "zemlju"),
        ("afterPreposition", "فِي الْأَرْضِ", "na zemlji"), ("afterPreposition", "عَلَى الْأَرْضِ", "na zemlji"),
        ("possessor", "لَوْنُ الْأَرْضِ", "boja zemlje"), ("possessiveSuffix", "أَرْضُهُ", "njegova zemlja")]
    assert found[4].en == "the color of the earth"


# ---------------------------------------------------------------- the sentence gate

TABLE = sentence_gate.table_index([
    (Cell(SINGULAR, DEFINITE, NOMINATIVE), "ٱلْبَيْتُ"), (Cell(SINGULAR, DEFINITE, ACCUSATIVE), "ٱلْبَيْتَ"),
    (Cell(SINGULAR, DEFINITE, GENITIVE), "ٱلْبَيْتِ"), (Cell(SINGULAR, INDEFINITE, NOMINATIVE), "بَيْتٌ"),
    (Cell(SINGULAR, INDEFINITE, ACCUSATIVE), "بَيْتًا"),
])


def analyzer(word: str) -> list[dict]:
    """Every word but فِي is a known noun; بَابُ reads as construct."""
    if word == "فِي":
        return [{"pos": "prep"}]
    return [{"pos": "noun", "stt": "c" if word == "بَابُ" else "d", "gloss": "house;door;father;open"}]


def sentence(*words: str) -> Example:
    built = tuple(ExampleWord(word.lstrip("*"), "house", "kuća", is_target=word.startswith("*")) for word in words)
    return Example(" ".join(word.arabic for word in built), built, "en", "bs")


@pytest.mark.parametrize(("role", "words", "passes"), [
    ("object", ("فَتَحَ", "*الْبَيْتَ"), True),
    ("object", ("فَتَحَ", "*الْبَيْتُ"), False),              # nominative where the object must be accusative
    ("subject", ("*الْبَيْتُ", "كَبِيرٌ"), True),
    ("preposition", ("فِي", "*الْبَيْتِ"), True),
    ("preposition", ("فَتَحَ", "*الْبَيْتِ"), False),          # a genitive with no preposition before it
    ("preposition", ("نَامَ", "*لِلْبَيْتِ"), True),           # لِ + the article without its alif
    ("possession", ("بَابُ", "*الْبَيْتِ"), True),
    ("possession", ("فِي", "*الْبَيْتِ"), False),
    ("subject", ("*بَيْتُ", "الرَّجُلِ"), True),               # the construct form of بَيْتٌ
    ("subject", ("*الْبَيْتِ",), False),
])
def test_the_noun_is_held_to_its_table_and_its_role(role, words, passes):
    checked = sentence_gate.check_sentence(sentence(*words), role, TABLE, analyzer)
    assert checked.passed is passes


@pytest.mark.parametrize(("indefinite", "construct"), [
    ("رَبٌّ", "رَبُّ"), ("كِتَابًا", "كِتَابَ"), ("كِتاباً", "كِتابَ"), ("شَيْئًا", "شَيْئَ"), ("مَوْلًى", "مَوْلَى"), ("مُؤْمِنُونَ", None),
])
def test_the_construct_form_drops_nunation(indefinite, construct):
    assert sentence_gate.construct_form(indefinite) == construct


def test_a_noun_on_alif_maqsura_keeps_it_in_construct():
    index = sentence_gate.table_index([(Cell(SINGULAR, INDEFINITE, NOMINATIVE), "مَوْلًى")])
    construct = index[spelling_key("مَوْلَى")]
    assert {cell.state for cell in construct} == {CONSTRUCT}


def test_a_maqsur_noun_gets_no_construct_cell():
    index = sentence_gate.table_index([(Cell(SINGULAR, INDEFINITE, ACCUSATIVE), "عَصًا")])
    assert "عَصَ" not in "".join(index)


# ---------------------------------------------------------------- the page

def test_a_noun_page_shows_table_cases_sentences_and_forms():
    from fil.languages import LANGUAGES
    from fil.pages import interface_text, noun_render

    texts = interface_text.load()
    bosnian_language = next(language for language in LANGUAGES if language.code == "bs")
    cell = {"state": DEFINITE, "case": NOMINATIVE, "text": "ٱلْأَرْضُ", "source": "attested", "audio": "audio/a.m4a"}
    card = {"key": "أَرْض|أرض", "slug": "ard", "rank": 3, "lemma": "أَرْض", "root": "أرض", "kind": "noun", "gender": "F",
            "count": 461, "ayahCount": 400, "meaning": {"en": "earth", "bs": "zemlja"}, "verb": None,
            "picture": "pictures/ard.svg", "lemmaSpoken": None, "plurals": [],
            "table": [{"row": "S", "number": "S", "plural": None,
                       "cells": [cell, {"state": DEFINITE, "case": ACCUSATIVE, "text": "الْأَرْضَ", "source": "generated"}]}],
            "explanation": [{"role": "subject", "arabicCase": "NOM", "arabic": "ٱلْأَرْضُ", "en": "the earth", "bs": "zemlja",
                             "bosnianCase": "N", "quranic": False, "audio": None}],
            "sentences": [{"role": "object", "arabic": "سَقَى الْأَرْضَ", "spoken": None, "reviewed": True,
                           "translation": {"bs": "Zalio je zemlju.", "en": "He watered the land."},
                           "words": [{"arabic": "سَقَى", "target": False}, {"arabic": "الْأَرْضَ", "target": True}]}],
            "forms": [{"preposition": "فِي", "arabic": "ٱلْأَرْضِ", "count": 200, "first": "2:11", "audio": None,
                       "grammar": {"case": "GEN", "number": "S", "state": "definite", "possessor": None, "proclitics": []},
                       "gloss": {"en": "in the earth", "bs": "na zemlji"}}],
            "ayat": [], "ayatFile": "ayat/noun-ard.json", "ayatTranslations": {"en": "ayat/noun-ard.en.json"}}
    html = noun_render.noun_page(card, bosnian_language, texts["bs"], category="nature_sky")
    for expected in ("Padeži", 'data-audio="../../../audio/a.m4a"', "standardni pravopis", "na zemlji",
                     "bosanski nominativ", "<b>الْأَرْضَ</b>", "priroda i nebo", 'hreflang="en"', "../../../pictures/ard.svg"):
        assert expected in html
