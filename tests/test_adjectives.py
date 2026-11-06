"""The adjectives pilot: declension by rule, Bosnian and English agreement, the agreement rule,
the sentence gate that holds an adjective to its noun, composed glosses, the table, selection.

Golden values are hand-checked Arabic and Bosnian.
"""

from __future__ import annotations

import unicodedata

import pytest

from fil.adjectives import agreement, bosnian, declension, english, explanation, sentence_gate
from fil.adjectives.compose import AdjectiveGlossing, compose
from fil.adjectives.model import AdjectiveMeaning, AdjectiveTable, DescribedNouns, Elative, InvalidAdjectiveData, \
    parse_meaning
from fil.adjectives.selection import ELATIVE, next_adjectives, skip_reason
from fil.adjectives.table import RULE, build_adjective_table
from fil.examples import Example, ExampleWord
from fil.nouns import gate
from fil.nouns.bosnian import BosnianNoun
from fil.nouns.compose import Composed, Skipped
from fil.nouns.english import EnglishNoun
from fil.nouns.model import (ACCUSATIVE, ADJECTIVE, CONSTRUCT, DEFINITE, DUAL, FEMININE, GENITIVE, INDEFINITE,
                             MASCULINE, NOMINATIVE, NOUN, PLURAL, SINGULAR, Cell, NounLemma, NounOccurrence, NounParts)
from fil.nouns.spelling import imlai, skeleton, spelling_key
from fil.nouns.table import DOCUMENTED

# ---------------------------------------------------------------- declension by rule

def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)



def test_a_broken_triptote_plural_is_declined_with_nunation():
    assert declension.declined("كِبَار") == {
        (DEFINITE, NOMINATIVE): "الْكِبَارُ", (DEFINITE, ACCUSATIVE): "الْكِبَارَ", (DEFINITE, GENITIVE): "الْكِبَارِ",
        (INDEFINITE, NOMINATIVE): "كِبَارٌ", (INDEFINITE, ACCUSATIVE): "كِبَارًا", (INDEFINITE, GENITIVE): "كِبَارٍ"}


def test_a_plural_in_aa_is_a_diptote_and_the_sun_letter_is_doubled():
    forms = declension.declined("عُظَمَاء")
    assert (forms[(INDEFINITE, NOMINATIVE)], forms[(INDEFINITE, GENITIVE)], forms[(DEFINITE, GENITIVE)]) == \
        ("عُظَمَاءُ", "عُظَمَاءَ", "الْعُظَمَاءِ")
    assert declension.declined("شِدَاد")[(DEFINITE, NOMINATIVE)] == "الشِّدَادُ"


def test_an_afal_singular_takes_no_nunation_when_its_pattern_says_so():
    assert declension.declined("آخَر", is_diptote_pattern=True)[(INDEFINITE, NOMINATIVE)] == "آخَرُ"


def test_the_dual_and_the_sound_plurals():
    assert declension.dual("كَبِيرَة")[(INDEFINITE, ACCUSATIVE)] == "كَبِيرَتَيْنِ"
    assert declension.dual("كَبِير")[(DEFINITE, NOMINATIVE)] == "الْكَبِيرَانِ"
    assert declension.sound_plural("كَبِيرَة")[(INDEFINITE, ACCUSATIVE)] == "كَبِيرَاتٍ"
    assert declension.sound_plural("صَابِر")[(DEFINITE, NOMINATIVE)] == "الصَّابِرُونَ"


def test_a_doubled_ya_is_a_consonant_but_a_hamza_or_long_vowel_is_refused():
    assert declension.declined("حَيّ")[(INDEFINITE, ACCUSATIVE)] == "حَيًّا"
    for stem in ("بَرِيء", "أَعْمَى", "مَوْتَى"):
        with pytest.raises(declension.CannotDecline):
            declension.declined(stem)


def test_every_rule_form_passes_the_noun_gate():
    for number, forms in ((SINGULAR, declension.declined("كَبِير")), (DUAL, declension.dual("كَبِيرَة")),
                          (PLURAL, declension.sound_plural("كَبِيرَة")), (PLURAL, declension.sound_plural("كَبِير"))):
        lemma = "كَبِيرَة" if "كَبِيرَت" in forms[(DEFINITE, NOMINATIVE)] or "ات" in forms[(DEFINITE, NOMINATIVE)] else "كَبِير"
        for (state, case), text in forms.items():
            assert gate.problems(text, Cell(number, state, case), lemma) == (), text


def test_the_elative_is_a_diptote():
    assert declension.elative_nominative("أَكْبَر") == "أَكْبَرُ"
    assert declension.elative_nominative("أَشَدّ") == "أَشَدُّ"
    assert declension.elative_nominative("أَدْنَى") is None


# ---------------------------------------------------------------- Bosnian and English by rule

@pytest.mark.parametrize(("long_form", "gender", "number", "case", "expected"), [
    ("veliki", "f", "sg", "N", "velika"), ("veliki", "n", "sg", "N", "veliko"), ("veliki", "m", "sg", "G", "velikog"),
    ("veliki", "ma", "sg", "A", "velikog"), ("veliki", "m", "sg", "A", "veliki"), ("veliki", "f", "sg", "L", "velikoj"),
    ("veliki", "f", "pl", "N", "velike"), ("veliki", "n", "pl", "N", "velika"), ("veliki", "m", "pl", "D", "velikim"),
    ("loši", "m", "sg", "G", "lošeg"), ("vrući", "n", "sg", "N", "vruće"), ("zalutali", "n", "sg", "N", "zalutalo"),
])
def test_a_bosnian_adjective_agrees_with_its_bosnian_noun(long_form, gender, number, case, expected):
    assert bosnian.declined(long_form, gender, number, case) == expected


def test_only_a_masculine_singular_predicate_takes_the_short_form():
    assert bosnian.predicate("veliki", "velik", "m", "sg") == "velik"
    assert bosnian.predicate("veliki", "velik", "f", "sg") == "velika"
    assert bosnian.predicate("veliki", "velik", "m", "pl") == "veliki"


def test_an_indefinite_masculine_singular_attribute_takes_the_short_form() -> None:
    assert bosnian.attribute("jasni", "m", "sg", "N", short_form="jasan", is_definite=False) == "jasan"
    assert bosnian.attribute("jasni", "m", "sg", "N", short_form="jasan", is_definite=True) == "jasni"
    assert bosnian.attribute("jasni", "f", "sg", "N", short_form="jasan", is_definite=False) == "jasna"
    assert bosnian.attribute("jasni", "m", "sg", "G", short_form="jasan", is_definite=False) == "jasnog"
    assert bosnian.attribute("jasni", "m", "pl", "N", short_form="jasan", is_definite=False) == "jasni"


def test_a_bosnian_long_form_must_be_one_word_in_i():
    with pytest.raises(bosnian.InvalidBosnianAdjective):
        bosnian.validated_long_form("velik")


HOUSE, WATER = EnglishNoun("house", "houses"), EnglishNoun("water", "waters", is_countable=False)


def test_english_attributes_predicates_and_comparisons():
    assert english.attribute("big", HOUSE, SINGULAR, is_definite=False) == "a big house"
    assert english.attribute("old", HOUSE, SINGULAR, is_definite=False) == "an old house"
    assert english.attribute("other", HOUSE, SINGULAR, is_definite=False) == "another house"
    assert english.attribute("cold", WATER, SINGULAR, is_definite=False) == "cold water"
    assert english.attribute("big", HOUSE, PLURAL, is_definite=False) == "big houses"
    assert english.predicate("big", HOUSE, SINGULAR) == "The house is big."
    assert english.comparison("bigger", HOUSE, EnglishNoun("tree", "trees")) == "The house is bigger than the tree."


# ---------------------------------------------------------------- the agreement rule

def noun(gender: str, number: str, state: str, case: str, is_human: bool = False) -> agreement.NounReading:
    return agreement.NounReading(gender, Cell(number, state, case), is_human)


def adjective(gender: str, number: str, state: str, case: str) -> agreement.AdjectiveReading:
    return agreement.AdjectiveReading(gender, Cell(number, state, case))


def test_an_attribute_follows_its_noun_in_everything():
    assert agreement.is_attribute(adjective(MASCULINE, SINGULAR, INDEFINITE, NOMINATIVE),
                                  noun(MASCULINE, SINGULAR, INDEFINITE, NOMINATIVE))
    assert not agreement.is_attribute(adjective(MASCULINE, SINGULAR, DEFINITE, NOMINATIVE),
                                      noun(MASCULINE, SINGULAR, INDEFINITE, NOMINATIVE))
    assert not agreement.is_attribute(adjective(MASCULINE, SINGULAR, INDEFINITE, GENITIVE),
                                      noun(MASCULINE, SINGULAR, INDEFINITE, NOMINATIVE))
    assert agreement.is_attribute(adjective(MASCULINE, SINGULAR, DEFINITE, NOMINATIVE),
                                  noun(MASCULINE, SINGULAR, CONSTRUCT, NOMINATIVE))   # بَيْتُهُ الْكَبِيرُ


def test_a_plural_of_things_takes_the_feminine_singular_and_people_the_plural():
    houses = noun(MASCULINE, PLURAL, INDEFINITE, NOMINATIVE)
    men = noun(MASCULINE, PLURAL, INDEFINITE, NOMINATIVE, is_human=True)
    assert agreement.is_attribute(adjective(FEMININE, SINGULAR, INDEFINITE, NOMINATIVE), houses)
    assert not agreement.is_attribute(adjective(MASCULINE, PLURAL, INDEFINITE, NOMINATIVE), houses)
    assert agreement.is_attribute(adjective(MASCULINE, PLURAL, INDEFINITE, NOMINATIVE), men)


def test_a_predicate_is_indefinite_and_accusative_after_kana():
    subject = noun(MASCULINE, SINGULAR, DEFINITE, NOMINATIVE)
    assert agreement.is_predicate(adjective(MASCULINE, SINGULAR, INDEFINITE, NOMINATIVE), subject)
    assert agreement.is_predicate(adjective(MASCULINE, SINGULAR, INDEFINITE, ACCUSATIVE), subject, after_kana=True)
    assert not agreement.is_predicate(adjective(MASCULINE, SINGULAR, DEFINITE, NOMINATIVE), subject)


# ---------------------------------------------------------------- the sentence gate

ADJECTIVES = sentence_gate.adjective_index([
    (MASCULINE, Cell(SINGULAR, INDEFINITE, NOMINATIVE), "كَبِيرٌ"), (MASCULINE, Cell(SINGULAR, INDEFINITE, ACCUSATIVE), "كَبِيرًا"),
    (MASCULINE, Cell(SINGULAR, DEFINITE, NOMINATIVE), "الْكَبِيرُ"), (FEMININE, Cell(SINGULAR, INDEFINITE, NOMINATIVE), "كَبِيرَةٌ"),
    (FEMININE, Cell(SINGULAR, INDEFINITE, GENITIVE), "كَبِيرَةٍ"), (MASCULINE, Cell(PLURAL, INDEFINITE, NOMINATIVE), "كِبَارٌ"),
])
NOUNS = {spelling_key(text): (reading,) for text, reading in (
    ("بَيْتٌ", noun(MASCULINE, SINGULAR, INDEFINITE, NOMINATIVE)), ("الْبَيْتُ", noun(MASCULINE, SINGULAR, DEFINITE, NOMINATIVE)),
    ("شَجَرَةٌ", noun(FEMININE, SINGULAR, INDEFINITE, NOMINATIVE)), ("بُيُوتٍ", noun(MASCULINE, PLURAL, INDEFINITE, GENITIVE)),
    ("رِجَالٌ", noun(MASCULINE, PLURAL, INDEFINITE, NOMINATIVE, is_human=True)),
    ("بُيُوتٌ", noun(MASCULINE, PLURAL, INDEFINITE, NOMINATIVE)))}


def analyzer(word: str) -> list[dict]:
    return [{"pos": "noun"}]


def sentence(*words: str) -> Example:
    built = tuple(ExampleWord(word.lstrip("*"), "x", "x", is_target=word.startswith("*")) for word in words)
    return Example(" ".join(word.arabic for word in built), built, "en", "bs")


@pytest.mark.parametrize(("role", "words", "passes"), [
    ("masculine", ("هَذَا", "بَيْتٌ", "*كَبِيرٌ"), True),
    ("masculine", ("هَذَا", "بَيْتٌ", "*الْكَبِيرُ"), False),            # definiteness differs
    ("feminine", ("هَذِهِ", "شَجَرَةٌ", "*كَبِيرَةٌ"), True),
    ("feminine", ("هَذِهِ", "شَجَرَةٌ", "*كَبِيرٌ"), False),             # gender differs
    ("predicate", ("الْبَيْتُ", "*كَبِيرٌ"), True),
    ("predicate", ("كَانَ", "الْبَيْتُ", "*كَبِيرًا"), True),            # accusative after كَانَ
    ("predicate", ("الْبَيْتُ", "*كَبِيرًا"), False),
    ("plural", ("فِي", "بُيُوتٍ", "*كَبِيرَةٍ"), True),                  # things: feminine singular
    ("plural", ("جَاءَ", "رِجَالٌ", "*كِبَارٌ"), True),                  # people: the plural
    ("plural", ("هَذِهِ", "بُيُوتٌ", "*كِبَارٌ"), False),                # things never take the masculine plural
    ("masculine", ("رَأَيْتُ", "*كَبِيرًا"), False),                    # no noun to describe
])
def test_the_adjective_must_agree_with_a_studied_noun_in_its_role(role, words, passes):
    checks = sentence_gate.check_sentence(sentence(*words), role, ADJECTIVES, NOUNS, analyzer)
    assert checks.passed is passes


# ---------------------------------------------------------------- the table

MEANING = AdjectiveMeaning(lemma="كَبِير", root="كبر", en="large, big", bs="velik", bs_short="velik", bs_long="veliki",
                           feminine="كَبِيرَة", has_feminine_lemma=False, pattern="فَعِيل", category="size_quantity",
                           nouns=DescribedNouns("بَيْت|بيت", "شَجَرَة|شجر", "بَيْت|بيت", "رِجال|رجل"),
                           masculine_plural="كِبَار", elative=Elative("bigger", "veći"))
LEMMA = NounLemma("كَبِير", "كبر", ADJECTIVE, MASCULINE, 40, 137, None, (), 0, (), None)


def test_without_a_generator_the_rule_and_the_drafters_plural_fill_the_table():
    table = build_adjective_table(LEMMA, MEANING, [], [], generator=None)
    rows = {(gender, row.row): row for gender in (MASCULINE, FEMININE) for row in table.side(gender).rows}
    assert set(rows) == {(MASCULINE, "S"), (MASCULINE, "D"), (MASCULINE, "P"), (FEMININE, "S"), (FEMININE, "D"), (FEMININE, "P")}
    assert rows[(MASCULINE, "P")].text(INDEFINITE, NOMINATIVE) == "كِبَارٌ"
    assert {cell.source for cell in rows[(MASCULINE, "P")].cells} == {DOCUMENTED}
    assert rows[(FEMININE, "P")].text(DEFINITE, GENITIVE) == "الْكَبِيرَاتِ"
    assert {cell.source for cell in rows[(FEMININE, "S")].cells} == {RULE}


def test_a_meaning_needs_its_nouns_and_a_known_category():
    entry = {"en": "large", "bs": "velik", "bsShort": "velik", "bsLong": "veliki", "feminine": "كَبِيرَة",
             "pattern": "فَعِيل", "category": "size_quantity", "nouns": {"masculine": "بَيْت|بيت"}}
    with pytest.raises(InvalidAdjectiveData, match="feminine noun"):
        parse_meaning("كَبِير|كبر", entry)
    with pytest.raises(InvalidAdjectiveData, match="category"):
        parse_meaning("كَبِير|كبر", {**entry, "category": "sizes", "nouns": {"masculine": "a", "feminine": "b"}})


# ---------------------------------------------------------------- the agreement examples

def described(gender: str, cells: dict, english_noun: EnglishNoun, bosnian_cells: dict, genders: dict) -> explanation.DescribedNoun:
    return explanation.DescribedNoun(gender, lambda number, state, case: cells.get((number, state, case)), english_noun,
                                     BosnianNoun(bosnian_cells, genders, {}))


def test_the_examples_are_composed_from_cells_and_agree_in_bosnian_with_the_bosnian_noun():
    house = described(MASCULINE, {(SINGULAR, INDEFINITE, NOMINATIVE): "بَيْتٌ", (SINGULAR, DEFINITE, NOMINATIVE): "ٱلْبَيْتُ",
                                  (PLURAL, INDEFINITE, NOMINATIVE): "بُيُوتٌ"},
                      HOUSE, {"sg|N": "kuća", "pl|N": "kuće"}, {"sg": "f", "pl": "f"})
    tree = described(FEMININE, {(SINGULAR, INDEFINITE, NOMINATIVE): "شَجَرَةٌ", (SINGULAR, DEFINITE, GENITIVE): "الشَّجَرَةِ"},
                     EnglishNoun("tree", "trees"), {"sg|N": "drvo", "sg|G": "drveta"}, {"sg": "n"})
    table = build_adjective_table(LEMMA, MEANING, [], [], generator=None)
    table = AdjectiveTable(table.key, table.masculine, table.feminine, elative="أَكْبَرُ")
    nouns = {"بَيْت|بيت": house, "شَجَرَة|شجر": tree, "رِجال|رجل": house}
    found = {example.kind: example for example in explanation.examples(MEANING, table, nouns, table.elative)}
    assert (found["indefinite"].arabic, found["indefinite"].en, found["indefinite"].bs) == ("بَيْتٌ كَبِيرٌ", "a large house", "velika kuća")
    assert found["definite"].arabic == "الْبَيْتُ الْكَبِيرُ"                     # the Quran's ٱ in its standard spelling
    assert (found["feminine"].arabic, found["feminine"].bs) == ("شَجَرَةٌ كَبِيرَةٌ", "veliko drvo")
    assert found["thingPlural"].arabic == "بُيُوتٌ كَبِيرَةٌ"
    assert (found["predicate"].arabic, found["predicate"].bs) == ("الْبَيْتُ كَبِيرٌ", "Kuća je velika.")
    assert (found["elative"].arabic, found["elative"].bs) == ("الْبَيْتُ أَكْبَرُ مِنَ الشَّجَرَةِ", "Kuća je veća od drveta.")


# ---------------------------------------------------------------- composed glosses

def occurrence(gender: str, number: str, state: str, case: str, proclitics=(), preposition=None) -> NounOccurrence:
    parts = NounParts(tuple(proclitics), state == DEFINITE, governing_preposition=preposition)
    return NounOccurrence(1, 1, 1, "x", "x", "أَلِيم", "ألم", ADJECTIVE, gender, number, case, state, None, parts)


PAINFUL = AdjectiveGlossing("painful", "bolni", "bolan")


def test_a_quranic_form_is_glossed_in_its_gender_and_number():
    assert compose([occurrence(MASCULINE, SINGULAR, INDEFINITE, ACCUSATIVE)], PAINFUL) == Composed("painful", "bolan", "N")
    assert compose([occurrence(FEMININE, SINGULAR, DEFINITE, GENITIVE, ("and",))], PAINFUL) == \
        Composed("and the painful", "i bolna", "N")


def test_a_form_used_as_a_noun_or_a_dual_keeps_its_label():
    assert isinstance(compose([occurrence(MASCULINE, PLURAL, DEFINITE, GENITIVE, preposition="مِن")], PAINFUL), Skipped)
    assert isinstance(compose([occurrence(MASCULINE, DUAL, INDEFINITE, NOMINATIVE)], PAINFUL), Skipped)


# ---------------------------------------------------------------- selection

def lemma(text: str, count: int, kind: str = ADJECTIVE, root: str = "كبر") -> NounLemma:
    return NounLemma(text, root, kind, MASCULINE, count, 1, None, (), 0, (), None)


def test_elatives_and_held_back_wait_and_a_separate_feminine_counts_with_its_masculine():
    lemmas = [lemma("أَكْبَر", 90), lemma("غَفُور", 80, root="غفر"), lemma("كَبِيرَة", 50), lemma("كَبِير", 40),
              lemma("صَغِير", 60, root="صغر"), lemma("بَيْت", 500, kind=NOUN, root="بيت")]
    chosen, skipped = next_adjectives(lemmas, 2, studied=())
    assert [found.lemma for found in chosen] == ["كَبِير", "صَغِير"]          # 40 + 50 of its feminine
    assert {found.lemma: reason for found, reason in skipped} == {"أَكْبَر": ELATIVE, "غَفُور": "held back for the owner"}
    assert skip_reason(lemma("كَبِير", 1), studied_nouns=["كَبِير|كبر"]) == "taught as a noun"


# ---------------------------------------------------------------- spelling

@pytest.mark.parametrize(("uthmani", "standard"), [
    ("ٱلْعَلِيمُ", "الْعَلِيمُ"), ("كِتَٰبٌ", "كِتَابٌ"), ("ٱلْءَاخَرُ", "الْآخَرُ"), ("ءَاخَرُونَ", "آخَرُونَ"),
    ("بَرِىٓءٌ", "بَرِيءٌ"), ("عَرَبِىٌّ", "عَرَبِيٌّ"), ("ٱلْأُخْرَىٰٓ", "الْأُخْرَى"), ("بَرِيٓـُٔونَ", "بَرِيئُونَ"),
])
def test_a_quranic_cell_is_shown_in_standard_spelling_as_the_same_word(uthmani, standard):
    assert imlai(uthmani) == standard
    assert spelling_key(imlai(uthmani)) == spelling_key(uthmani)


def test_madda_right_after_the_article_is_hamza_and_alif():
    assert skeleton("الْآخَرُونَ") == skeleton("ٱلْءَاخَرُونَ") == "الءاخرون"
    assert skeleton("قَآئِم") == "قاءم"          # a medial madd sign is only a long alif


# ---------------------------------------------------------------- the page

def test_an_adjective_page_shows_its_table_agreement_sentences_and_links():
    from fil.languages import LANGUAGES
    from fil.pages import adjective_render, interface_text, render

    texts = interface_text.load()
    english_language = next(language for language in LANGUAGES if language.code == "en")
    cell = {"state": INDEFINITE, "case": NOMINATIVE, "text": "كَبِيرٌ", "source": "attested", "audio": "audio/k.m4a"}
    card = {"key": "كَبِير|كبر", "slug": "kabir", "rank": 137, "lemma": "كَبِير", "root": "كبر", "count": 47, "ayahCount": 40,
            "meaning": {"en": "large, big", "bs": "velik"}, "pattern": "فَعِيل", "category": "size_quantity",
            "feminine": "كَبِيرَة", "feminineSpoken": None, "lemmaSpoken": "audio/k.m4a", "verb": None,
            "elative": {"arabic": "أَكْبَرُ", "spoken": None, "count": 24, "en": "bigger", "bs": "veći"},
            "table": [{"row": "S", "number": "S", "plural": None, "gender": MASCULINE, "cells": [cell]}],
            "explanation": [{"kind": "thingPlural", "arabic": "بُيُوتٌ كَبِيرَةٌ", "en": "large houses", "bs": "velike kuće",
                             "audio": None}],
            "sentences": [], "forms": [], "ayat": [], "ayatFile": "ayat/adjective-kabir.json",
            "ayatTranslations": {"en": "ayat/adjective-kabir.en.json"}}
    html = adjective_render.adjective_page(card, english_language, texts["en"],
                                           nouns_of_root=[{"key": "كِبَر|كبر", "slug": "kibar", "lemma": "كِبَر",
                                                           "root": "كبر", "meaning": {"en": "old age", "bs": "starost"}}])
    assert 'data-audio="../../../audio/k.m4a"' in html and "بُيُوتٌ كَبِيرَةٌ" in html and "large houses" in html
    assert "أَكْبَرُ" in html and "../../../en/noun/kibar/" in html
    assert render.ADJECTIVES and 'href="../../../en/adjective/"' in html
    listing = adjective_render.adjective_index([card], english_language, texts["en"])
    assert 'data-category="size_quantity"' in listing and "kabir/" in listing
