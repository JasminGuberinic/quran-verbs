"""The pronouns (Zamjenice): read from the corpus by their citation form, gated and paged by the particle engine.

Ground truth: the corpus gives an independent pronoun no lemma and files every demonstrative under ذا
and every relative under الَّذِي; the reader names them as a grammar does (هُوَ, ذَٰلِكَ, الَّذِينَ), leaves
out the suffixes and the pronouns after a preposition, and the stored pages pass the same gate as the
particles.
"""

from __future__ import annotations

import shutil

import pytest

from fil.corpus.parse import parse_segment
from fil.corpus.pronouns import iter_pronoun_occurrences
from fil.languages import LANGUAGES
from fil.particles import gate
from fil.particles.model import CorpusTag
from fil.pages import particle_render, render, seo
from fil.resources import QAC_MORPHOLOGY
from fil.stages.particles import PRONOUNS

needs_corpus = pytest.mark.skipif(not QAC_MORPHOLOGY.exists(), reason="the corpus is not downloaded")
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _read(*lines: str) -> list[tuple[str, str, int]]:
    return [(occurrence.lemma, str(occurrence.corpus_tag), occurrence.word)
            for occurrence in iter_pronoun_occurrences([parse_segment(line) for line in lines])]


# ---------------------------------------------------------------- the reader

def test_an_independent_pronoun_is_named_by_person_gender_and_number():
    assert _read("2:5:7:1\tهُمُ\tN\tPRON|3MP", "85:14:1:1\tوَ\tP\tCONJ|PREF|LEM:و", "85:14:1:2\tهُوَ\tN\tPRON|3MS") == [
        ("هُمْ", "PRON", 7), ("هُوَ", "PRON", 1)]


def test_a_suffix_and_a_pronoun_after_a_preposition_are_not_independent_pronouns():
    assert _read("2:3:7:1\tرَزَقْ\tV\tPERF|VF:1|ROOT:رزق|LEM:رَزَقَ|1P", "2:3:7:2\tنَٰ\tN\tPRON|SUFF|1P",
                 "2:3:7:3\tهُمْ\tN\tPRON|SUFF|3MP",
                 "2:11:3:1\tلَ\tP\tP|PREF|LEM:ل", "2:11:3:2\tهُمْ\tN\tPRON|3MP") == []


def test_an_emphatic_lam_before_a_pronoun_leaves_it_independent():
    assert _read("3:62:3:1\tلَ\tP\tEMPH|PREF|LEM:ل", "3:62:3:2\tهُوَ\tN\tPRON|3MS") == [("هُوَ", "PRON", 3)]


def test_a_demonstrative_is_near_with_ha_and_far_with_the_kaf_of_address():
    assert _read("2:2:1:1\tذَٰ\tN\tDEM|LEM:ذا|MS", "2:2:1:2\tلِ\tP\tDIST|SUFF", "2:2:1:3\tكَ\tP\tADDR|SUFF|M",
                 "2:25:20:1\tهَٰ\tP\tATT|PREF|LEM:ه", "2:25:20:2\tذَا\tN\tDEM|LEM:ذا|MS",
                 "2:5:1:1\tأُو۟لَٰٓئِ\tN\tDEM|LEM:ذا|P", "2:5:1:2\tكَ\tP\tADDR|SUFF|M",
                 "2:255:21:1\tذَا\tN\tDEM|LEM:ذا|MS") == [
        ("ذَٰلِكَ", "DEM", 1), ("هَٰذَا", "DEM", 20), ("أُولَٰئِكَ", "DEM", 1), ("ذا", "DEM", 21)]   # مَن ذَا keeps ذا


def test_a_relative_is_named_by_gender_and_number_and_iyya_by_its_lemma():
    relative = "الَّذِي"          # the corpus's spelling: shadda before fatḥa
    assert _read(f"1:7:2:1\tٱلَّذِينَ\tN\tREL|LEM:{relative}|MP", f"3:131:3:1\tٱلَّتِىٓ\tN\tREL|LEM:{relative}|FS",
                 "1:5:1:1\tإِيَّاكَ\tN\tPRON|LEM:إِيّا|2MS", "2:3:6:3\tمَّا\tN\tREL|LEM:ما") == [
        ("الَّذِينَ", "REL", 2), ("الَّتِي", "REL", 3), ("إِيّا", "PRON", 1)]                              # relative مَا is a particle


# ---------------------------------------------------------------- the stored pronouns, against the corpus

def test_the_stored_pronouns_load_most_frequent_first():
    pronouns = PRONOUNS.load()
    assert len(pronouns) == 17 and pronouns[0].slug == "alladhina"
    assert [pronoun.count for pronoun in pronouns] == sorted((pronoun.count for pronoun in pronouns), reverse=True)


@pytest.fixture(scope="module")
def corpus():
    return PRONOUNS.concordance()


@needs_corpus
def test_every_stored_pronoun_passes_the_corpus_gate(corpus):
    assert gate.problems(PRONOUNS.load(), corpus) == []


@needs_corpus
@pytest.mark.parametrize(("lemma", "tag", "count"), [
    ("هُوَ", "PRON", 481), ("هُمْ", "PRON", 442), ("أَنَا", "PRON", 68), ("إِيّا", "PRON", 24),
    ("ذَٰلِكَ", "DEM", 479), ("هَٰذَا", "DEM", 226), ("أُولَٰئِكَ", "DEM", 206), ("الَّذِينَ", "REL", 1080), ("الَّذِي", "REL", 304),
])
def test_golden_counts_come_from_the_corpus(corpus, lemma, tag, count):
    assert len(corpus.occurrences(lemma, CorpusTag.parse(tag))) == count


# ---------------------------------------------------------------- pages

@pytest.fixture(scope="module")
def texts():
    from fil.pages import interface_text
    return interface_text.load()


def _language(code: str):
    return next(language for language in LANGUAGES if language.code == code)


def _card() -> dict:
    ayah = {"ref": "112:1", "audio": None, "why": {"bs": "On", "en": "He"}, "translation": {},
            "words": [{"text": "قُلْ", "hit": False}, {"text": "هُوَ", "hit": True, "audio": None}], "studied": []}
    use = {"key": "subject", "kind": "personalPronoun", "title": {"bs": "Subjekat", "en": "Subject"},
           "explanation": {"bs": "Subjekat.", "en": "The subject."}, "effect": None, "count": 481, "ayat": [ayah]}
    return {"slug": "huwa", "arabic": "هُوَ", "audio": None, "count": 481, "meaning": {"bs": "on", "en": "he"},
            "grammar": {"bs": "Lična zamjenica.", "en": "A personal pronoun."}, "kinds": ["personalPronoun"],
            "preposition": None, "caseNoun": None, "uses": [use], "sources": ["Muġnī"], "unvoiced": []}


@needs_node
def test_a_pronoun_page_lives_in_its_own_section_and_marks_it(texts):
    html = particle_render.particle_page(_card(), _language("bs"), texts["bs"], published={render.PARTICLES},
                                         section=particle_render.PRONOUNS)
    assert "lična zamjenica" in html and "zamjenice u Kur&#x27;anu" in html
    assert 'hreflang="en" href="https://jasminguberinic.github.io/quran-verbs/en/pronoun/huwa/"' in html
    assert 'href="../../../bs/zamjenica/" aria-current="true">Zamjenice</a>' in html
    assert 'href="../../../bs/cestica/">Čestice</a>' in html


@needs_node
def test_the_list_of_pronouns_links_every_pronoun(texts):
    html = particle_render.particle_index([_card()], _language("en"), texts["en"], published=(),
                                          section=particle_render.PRONOUNS)
    assert 'href="huwa/"' in html and "Pronouns: he, this, the one who" in html


@needs_node
@pytest.mark.parametrize("code", [language.code for language in LANGUAGES])
def test_the_top_bar_leads_to_the_pronouns_only_in_bosnian_and_english(texts, code):
    bar = render.top_bar(texts[code], "../", _language(code), "", section=render.VERBS, published={render.PRONOUNS})
    assert (f'href="../{code}/{seo.PRONOUN_FOLDERS.get(code)}/"' in bar) == (code in seo.PRONOUN_FOLDERS)
