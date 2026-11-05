"""Collectives, singulatives and male/female pairs (fil.nouns.relations): the reviewed data,
its validation, what the table and the Bosnian declension do with it, and the page."""

from __future__ import annotations

import pytest

from fil import noun_store
from fil.languages import LANGUAGES
from fil.nouns import bosnian
from fil.nouns.bosnian import BosnianNoun, Phrase
from fil.nouns.model import ATTESTED, GENERATED, PLURAL, SINGULAR, Cell, NounLemma, ParadigmCell, PluralForm
from fil.nouns.relations import (COLLECTIVE, FEMALE, MALE, ONE, OF_COLLECTIVE, ORDINARY, PAIR, SINGULATIVE,
                                 InvalidNounRelation, likely_collective, parse_relations)
from fil.nouns.studied import NounTable, TableRow
from fil.nouns.table import as_collective
from fil.pages import noun_render
from fil.pages.interface_text import load

RELATIONS = noun_store.load_relations()


# ---------------------------------------------------------------- golden: the pilot's nouns

def test_ibil_is_a_feminine_collective_whose_one_is_a_male_or_a_she_camel():
    ibil = RELATIONS["إِبِل|أبل"]
    assert (ibil.kind, ibil.agreement) == (COLLECTIVE, "F")
    assert {(word.role, word.arabic, word.gender) for word in ibil.related} == {
        (MALE, "جَمَلٌ", "M"), (FEMALE, "نَاقَةٌ", "F")}


@pytest.mark.parametrize("key, kind, related", [
    ("قَوْم|قوم", COLLECTIVE, set()),
    ("ناس|أنس", COLLECTIVE, {(ONE, "إِنْسَانٌ")}),
    ("نَخْل|نخل", COLLECTIVE, {(ONE, "نَخْلَةٌ")}),
    ("طَيْر|طير", COLLECTIVE, {(ONE, "طَائِرٌ")}),
    ("زَيْتُون|زيت", COLLECTIVE, {(ONE, "زَيْتُونَةٌ")}),
    ("شَجَرَة|شجر", SINGULATIVE, {(OF_COLLECTIVE, "شَجَرٌ")}),
    ("بَقَرَة|بقر", SINGULATIVE, {(OF_COLLECTIVE, "بَقَرٌ"), (MALE, "ثَوْرٌ")}),
    ("عَبْد|عبد", PAIR, {(FEMALE, "أَمَةٌ")}),
])
def test_the_pilot_nouns_are_what_arabic_grammar_says(key, kind, related):
    relation = RELATIONS[key]
    assert relation.kind == kind
    assert {(word.role, word.arabic) for word in relation.related} == related


def test_the_ibil_table_is_declined_in_every_case_as_a_triptote_with_no_dual_or_plural():
    table = noun_store.load_tables()["إِبِل|أبل"]
    assert [row.row for row in table.rows] == ["S"]
    row = table.rows[0]
    assert [row.text(state, case) for state in ("definite", "indefinite") for case in ("NOM", "ACC", "GEN")] == [
        "الْإِبِلُ", "الْإِبِلَ", "ٱلْإِبِلِ", "إِبِلٌ", "إِبِلًا", "إِبِلٍ"]


def test_every_collective_table_has_its_own_row_and_only_quranic_plurals():
    tables = noun_store.load_tables()
    for key, relation in RELATIONS.items():
        if relation.is_collective:
            assert as_collective(tables[key]) == tables[key], key


def test_the_pilot_collectives_have_four_practice_sentences():
    roles = {(sentence.key, sentence.role) for sentence in noun_store.load_sentences() if sentence.example.is_shippable}
    for key in ("إِبِل|أبل", "قَوْم|قوم", "ناس|أنس", "نَخْل|نخل", "طَيْر|طير"):
        assert {role for found, role in roles if found == key} == {"subject", "object", "preposition", "possession"}, key


def test_a_collective_declined_in_the_bosnian_plural_takes_a_plural_possessive():
    camels = BosnianNoun(cells={"sg|N": "deve"}, genders={"sg": "f"}, prepositions={}, plural_numbers=frozenset({"sg"}))
    assert bosnian.phrase(camels, Phrase(possessor="3MS")) == "njegove deve"


def test_pluralforms_must_name_a_number():
    entry = {"cells": {}, "genders": {}, "prepositions": dict.fromkeys(bosnian.ARABIC_PREPOSITIONS, "-"),
             "pluralForms": ["many"]}
    with pytest.raises(bosnian.InvalidBosnianNoun, match="pluralForms"):
        bosnian.validated({"x|y": entry}, {})


# ---------------------------------------------------------------- validation

def _entry(**changes):
    return {"kind": COLLECTIVE, "agreement": "F", "why": "reviewed",
            "related": [{"role": FEMALE, "ar": "نَاقَةٌ", "gender": "F", "en": "she-camel", "bs": "deva (ženka)"}],
            **changes}


@pytest.mark.parametrize("entry, problem", [
    (_entry(why=""), "why"),
    (_entry(agreement=None), "agreement"),
    (_entry(kind=PAIR), "only a collective has an agreement"),
    (_entry(kind="plural"), "kind must be"),
    (_entry(related=[{"role": FEMALE, "ar": "نَاقَةٌ", "gender": "M", "en": "x", "bs": "x"}]), "a female with gender"),
    (_entry(related=[{"role": FEMALE, "ar": "النَّاقَةُ", "gender": "F", "en": "x", "bs": "x"}]), "with the article"),
    (_entry(related=[{"role": FEMALE, "ar": "نَاقَةً", "gender": "F", "en": "x", "bs": "x"}]), "NOM ending"),
    (_entry(related=[{"role": FEMALE, "ar": "نَاقَةٌ", "gender": "F", "en": "x", "bs": "x", "lemma": "جَمَل|جمل"}]),
     "not the letters"),
    (_entry(related=[{"role": OF_COLLECTIVE, "ar": "شَجَرٌ", "gender": "M", "en": "x", "bs": "x"}]), "has no"),
    ({"kind": SINGULATIVE, "why": "x"}, "names its collective"),
    ({"kind": ORDINARY, "why": "x", "related": _entry()["related"]}, "relates to nothing"),
])
def test_a_bad_relation_is_refused_by_name(entry, problem):
    with pytest.raises(InvalidNounRelation, match=problem):
        parse_relations({"إِبِل|أبل": entry})


# ---------------------------------------------------------------- the batch check

def _lemma(lemma: str, root: str, numbers=(SINGULAR,), plurals=()) -> NounLemma:
    return NounLemma(lemma=lemma, root=root, kind="noun", gender="M", count=1, rank=1, verb_form=None,
                     plurals=plurals, dual_count=0, forms=(), linked_verb=None, numbers=numbers)


def test_the_batch_check_flags_likely_collectives():
    palm, palms = _lemma("وَرَقَة", "ورق"), _lemma("وَرَق", "ورق")   # leaves: not in the known list
    people = _lemma("أَناسِيّ", "أنس", numbers=(PLURAL,), plurals=(PluralForm("أَنَاسِيَّ", "broken", 1),))
    catalogue = [palm, palms, people, _lemma("بَيْت", "بيت")]
    assert likely_collective(_lemma("إِبِل", "أبل"), catalogue) == "known collective"
    assert "-ة" in likely_collective(palms, catalogue)
    assert "without -ة" in likely_collective(palm, catalogue)
    assert "only ever plural" in likely_collective(people, catalogue)
    assert likely_collective(catalogue[3], catalogue) is None


def test_as_collective_drops_a_dual_and_a_generated_plural_but_keeps_a_quranic_one():
    def row(number: str, source: str) -> TableRow:
        return TableRow(number, number, None, (ParadigmCell(Cell(number, "definite", "NOM"), "x", source),))
    table = NounTable("k", (row("S", ATTESTED), row("D", GENERATED), row("P", GENERATED)))
    assert [found.row for found in as_collective(table).rows] == ["S"]
    quranic = NounTable("k", (row("S", ATTESTED), row("P", ATTESTED)))
    assert as_collective(quranic) == quranic


# ---------------------------------------------------------------- the page

def _card() -> dict:
    cell = {"state": "definite", "case": "GEN", "text": "ٱلْإِبِلِ", "source": "attested", "audio": None}
    return {"key": "إِبِل|أبل", "slug": "ibil", "rank": 1281, "lemma": "إِبِل", "root": "أبل", "kind": "noun",
            "gender": "M", "count": 2, "ayahCount": 2, "meaning": {"en": "camels", "bs": "deve"}, "verb": None,
            "picture": None, "lemmaSpoken": None, "plurals": [], "table": [{"row": "S", "number": "S", "plural": None,
                                                                           "cells": [cell]}],
            "explanation": [], "sentences": [], "forms": [], "ayat": [], "ayatFile": "ayat/noun-ibil.json",
            "ayatTranslations": {"en": "ayat/noun-ibil.en.json"},
            "relation": {"kind": COLLECTIVE, "agreement": "F", "related": [
                {"role": FEMALE, "arabic": "نَاقَةٌ", "gender": "F", "meaning": {"en": "she-camel", "bs": "deva (ženka)"},
                 "audio": None, "recited": False, "quranCount": 7, "slug": None}]}}


def test_the_page_names_a_collective_and_its_agreement_and_shows_its_female():
    bs = next(language for language in LANGUAGES if language.code == "bs")
    html = noun_render.noun_page(_card(), bs, load()["bs"], category="animals")
    assert "zbirna imenica (množina značenja)" in html and "ženski rod u slaganju" in html
    assert "muški rod" not in html.split("</header>")[0]
    assert "نَاقَةٌ" in html and "deva (ženka)" in html and "u Kur&#x27;anu 7×" in html
    assert ">zbirno<" in html and "jednina" not in html
