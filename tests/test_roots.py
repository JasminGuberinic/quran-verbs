"""Korijeni / Roots: the engine (pure), the gate, the pages, and golden roots from the corpus."""

from __future__ import annotations

import re
import shutil
from unicodedata import normalize
from pathlib import Path
from urllib.parse import unquote

import pytest

from fil.languages import LANGUAGES
from fil.nuances.model import Text
from fil.pages import interface_text, render, root_render, seo
from fil.resources import PAGES_DIR, QAC_MORPHOLOGY
from fil.roots import gate
from fil.roots.index import RootSources, alphabetical_key, root_pages
from fil.roots.model import (ADJECTIVES, NOUN_PAGE, NOUNS, PARTICIPLES, VERB, VERB_PAGE, VERBS, CoreIdea,
                             InvalidRootData, RootWord, StudiedPage, UnknownVerbForm, assign_slugs, parse_core_ideas,
                             slug_of, verb_pattern)

_LANGUAGE = {language.code: language for language in LANGUAGES}
_SAID = StudiedPage(kind=VERB_PAGE, slug="qala", meaning=Text(bs="reći", en="to say"), audio="audio/qala.m4a")
_SAYING = StudiedPage(kind=NOUN_PAGE, slug="qawl", meaning=Text(bs="izreka", en="saying"), audio=None)
_QWL_WORDS = (
    RootWord(key="قول_5", root="قول", arabic="تَقَوَّلَ", kind=VERB, count=2, form=5),
    RootWord(key="قَوْل|قول", root="قول", arabic="قَوْل", kind="verbal_noun", count=92, form=1),
    RootWord(key="قائِل|قول", root="قول", arabic="قائِل", kind="active_participle", count=5, form=1),
    RootWord(key="قول_1", root="قول", arabic="قالَ", kind=VERB, count=1618, form=1),
    RootWord(key="قِيل|قول", root="قول", arabic="قِيل", kind="noun", count=4),
)


def _sources(**changes) -> RootSources:
    base = dict(words=_QWL_WORDS, corpus_counts={"قول": 1721}, slugs={"قول": "q-w-l"},
                pages={"قول_1": (_SAID,), "قَوْل|قول": (_SAYING,)})
    return RootSources(**{**base, **changes})


# ---------------------------------------------------------------- the model

def test_a_root_page_name_reads_its_letters():
    assert [slug_of(root) for root in ("قول", "علم", "أمن", "شرك", "زلزل")] == ["q-w-l", "ayn-l-m", "a-m-n", "sh-r-k",
                                                                             "z-l-z-l"]


def test_roots_that_read_alike_give_the_more_frequent_the_plain_name():
    assert assign_slugs(["حمد", "همد", "سبل", "صبل"]) == {"حمد": "h-m-d", "همد": "h-m-d-2", "سبل": "s-b-l",
                                                         "صبل": "s-b-l-2"}


def test_verb_patterns_by_form_and_for_a_four_letter_root():
    assert [verb_pattern("فعل", form) for form in (1, 2, 4, 8, 10)] == ["فَعَلَ", "فَعَّلَ", "أَفْعَلَ", "اِفْتَعَلَ", "اِسْتَفْعَلَ"]
    assert verb_pattern("زلزل", 1) == "فَعْلَلَ" and verb_pattern("طمأن", 4) == "اِفْعَلَلَّ"
    with pytest.raises(UnknownVerbForm):
        verb_pattern("زلزل", 10)


def test_a_core_idea_is_bilingual_one_line_unquoted_and_verified():
    good = {"core": {"bs": "Govor iskazan riječima.", "en": "Speech put into words."},
            "verified": [{"source": "0502RaghibIsbahani.Mufradat.JK001150-ara1", "entries": ["قول"]}], "notes": "Confirmed."}
    assert parse_core_ideas({"قول": good})[0].entries == ("قول",)
    for broken in ({**good, "core": {"bs": "Govor."}}, {**good, "verified": []}, {**good, "notes": ""},
                   {**good, "core": {"bs": "„Govor“", "en": "Speech."}},
                   {**good, "verified": [{"source": "another book", "entries": ["قول"]}]},
                   {**good, "core": {"bs": "x" * 201, "en": "Speech."}}):
        with pytest.raises(InvalidRootData):
            parse_core_ideas({"قول": broken})


# ---------------------------------------------------------------- the engine

def test_a_root_lists_verbs_by_form_then_nouns_adjectives_participles_most_frequent_first():
    [page] = root_pages(_sources())
    assert [section for section, _ in page.sections] == [VERBS, NOUNS, PARTICIPLES]
    assert [[word.word.key for word in words] for _, words in page.sections] == [
        ["قول_1", "قول_5"], ["قَوْل|قول", "قِيل|قول"], ["قائِل|قول"]]
    assert [word.word.key for word in page.studied] == ["قول_1", "قَوْل|قول"]
    assert page.letters == "ق و ل" and page.listed_count == 1721


def test_a_word_shows_its_cards_meaning_else_only_a_vetted_one():
    [page] = root_pages(_sources(meanings={"قول_5": Text(bs="izmisliti", en="to fabricate"), "قول_1": Text(bs="x", en="x")}))
    meanings = {word.word.key: word.meaning for word in page.words}
    assert meanings["قول_1"].en == "to say"            # the card's, not the meaning file's
    assert meanings["قول_5"].en == "to fabricate"
    assert meanings["قِيل|قول"] is None                 # nothing vetted: Arabic and count only
    assert page.words[0].audio == "audio/qala.m4a"


def test_only_roots_with_a_studied_word_get_a_page_in_alphabetical_order():
    words = (*_QWL_WORDS, RootWord(key="أمن_1", root="أمن", arabic="أَمِنَ", kind=VERB, count=7, form=1),
             RootWord(key="بلو_1", root="بلو", arabic="بَلَا", kind=VERB, count=10, form=1))
    pages = root_pages(_sources(words=words, slugs={"قول": "q-w-l", "أمن": "a-m-n", "بلو": "b-l-w"},
                                pages={"قول_1": (_SAID,), "أمن_1": (_SAID,)}))
    assert [page.root for page in pages] == ["أمن", "قول"]
    assert alphabetical_key("أمن") < alphabetical_key("بلو") < alphabetical_key("قول")


def test_the_gate_finds_a_lost_studied_word_and_a_count_that_does_not_add_up():
    pages = root_pages(_sources())
    root_of_word = {word.key: word.root for word in _QWL_WORDS}
    studied = {"قول_1": (_SAID,), "قَوْل|قول": (_SAYING,)}
    assert gate.problems(pages, studied, root_of_word) == []
    assert gate.problems(pages, {**studied, "قائِل|قول": (_SAYING,)}, root_of_word) == [
        "قائِل|قول: on the page of قول, but not linked to all its pages"]
    assert gate.problems(pages, {"شيء|شيأ": (_SAYING,)}, root_of_word) == [
        "شيء|شيأ: a studied word that is not a word of the catalogues"]
    miscounted = root_pages(_sources(corpus_counts={"قول": 1722}))
    assert gate.problems(miscounted, studied, root_of_word) == [
        "قول: its words add up to 1721, the corpus has 1722 less 0 corrected"]
    corrected = root_pages(_sources(corpus_counts={"قول": 1722}, corrected_counts={"قول": 1}))
    assert gate.problems(corrected, studied, root_of_word) == []
    stray = CoreIdea(root="بلو", text=Text(bs="x", en="x"), entries=("بلا",), notes="x")
    assert gate.problems(pages, studied, root_of_word, [stray]) == ["بلو: a core idea for a root with no page"]


# ---------------------------------------------------------------- the pages

@pytest.fixture(scope="module")
def texts() -> dict[str, dict]:
    if shutil.which("node") is None:
        pytest.skip("the interface text needs Node")
    return interface_text.load()


def test_a_root_page_lists_every_word_and_links_the_studied_ones(texts):
    [page] = root_pages(_sources())
    html = root_render.root_page(page, _LANGUAGE["bs"], texts["bs"], published={render.ROOTS})
    assert "ق و ل" in html and "1721× u Kur'anu" in html and "5 riječi" in html
    assert 'href="../../../bs/qala/"' in html and 'href="../../../bs/imenica/qawl/"' in html
    assert "oblik V · " in html and "تَفَعَّلَ" in html and "أَقاوِيل" not in html
    assert html.count('class="studied"') == 2 and 'data-audio="../../../audio/qala.m4a"' in html
    assert "Osnovna ideja" not in html   # no core idea written: no line


def test_the_root_list_has_a_letter_index_and_a_search_that_needs_script(texts):
    pages = root_pages(_sources())
    html = root_render.root_index(pages, _LANGUAGE["en"], texts["en"], published={render.ROOTS})
    assert 'href="#letter-20"' in html and 'id="letter-20"' in html   # ق
    assert '<p class="root-search" hidden>' in html and "box.parentElement.hidden = false" in html
    assert 'data-search="قول q-w-l' in html and "قال" in root_render.search_terms(pages[0], "en")


def test_cards_link_their_root_where_the_root_pages_are_written():
    assert render.root_mark("قول", "bs", "../../", "q-w-l") == (
        '<a class="ar root" lang="ar" dir="rtl" href="../../bs/korijen/q-w-l/">ق و ل</a>')
    assert render.root_mark("قول", "tr", "../../", "q-w-l") == '<span class="ar root" lang="ar" dir="rtl">ق و ل</span>'
    assert "href" not in render.root_mark("قول", "en", "../", None)


def test_the_top_bar_leads_to_the_roots_once_they_are_published(texts):
    bar = render.top_bar(texts["en"], "../", _LANGUAGE["en"], "", section=render.VERBS, published={render.ROOTS})
    assert '<a href="../en/root/">Roots</a>' in bar
    assert "korijen" not in render.top_bar(texts["bs"], "../", _LANGUAGE["bs"], "", section=render.VERBS, published=())


# ---------------------------------------------------------------- golden roots, from the corpus

needs_corpus = pytest.mark.skipif(not QAC_MORPHOLOGY.exists(), reason="the corpus is not fetched")


@pytest.fixture(scope="module")
def corpus_pages():
    from fil.stages import roots as root_stage

    corpus = root_stage.RootCorpus.from_corpus()
    studied = root_stage.data_level_studied(corpus)
    core_ideas = root_stage.load_core_ideas()
    pages = root_stage.build_pages(corpus, studied, root_stage.vetted_meanings(), {}, core_ideas)
    return corpus, studied, core_ideas, {page.root: page for page in pages}


@needs_corpus
def test_golden_qwl_its_words_grouped_and_counted_as_the_corpus(corpus_pages):
    _corpus, _studied, _ideas, pages = corpus_pages
    page = pages["قول"]
    assert page.slug == "q-w-l" and page.corpus_count == 1722 and page.corrected_count == 0
    # Marks compared in canonical order: the corpus writes shadda before or after its vowel.
    grouped = {section: [(normalize("NFC", word.word.arabic), word.word.kind, word.word.count) for word in words]
               for section, words in page.sections}
    assert grouped == {
        VERBS: [("قالَ", VERB, 1618), (normalize("NFC", "تَقَوَّلَ"), VERB, 2)],
        NOUNS: [("قَوْل", "verbal_noun", 92), ("قِيل", "noun", 4), ("أَقاوِيل", "noun", 1)],
        PARTICIPLES: [("قائِل", "active_participle", 5)],
    }
    assert sum(count for words in grouped.values() for _, _, count in words) == 1722


@needs_corpus
def test_golden_alm_verbs_by_form_and_its_adjective(corpus_pages):
    page = corpus_pages[3]["علم"]
    verbs = dict(page.sections)[VERBS]
    assert [(word.word.form, word.word.count) for word in verbs] == [(1, 382), (2, 41), (5, 2)]
    assert ("عَلِيم", 163) in [(word.word.arabic, word.word.count) for word in dict(page.sections)[ADJECTIVES]]


@needs_corpus
def test_a_root_with_a_corrected_word_counts_it_out(corpus_pages):
    page = corpus_pages[3]["فطر"]
    assert (page.corpus_count, page.corrected_count, page.listed_count) == (20, 2, 18)


@needs_corpus
def test_gate_every_studied_word_on_its_root_page_and_every_root_adding_up(corpus_pages):
    corpus, studied, core_ideas, pages = corpus_pages
    assert gate.problems(list(pages.values()), studied, corpus.root_of_word, core_ideas) == []
    assert len(studied) > 1000 and len(core_ideas) >= 60


# ---------------------------------------------------------------- the built site

built = pytest.mark.skipif(not (PAGES_DIR / "bs" / "korijen" / "index.html").is_file(),
                           reason="build/pages has no root pages (run `fil pages`)")
_ROOT_LINK = re.compile(r'<a class="ar root" lang="ar" dir="rtl" href="([^"]+)">')


@built
@pytest.mark.parametrize("folder", ["bs/imenica", "en/adjective", "bs/pridjev"])
def test_every_built_card_links_a_root_page_that_links_it_back(folder):
    cards = sorted(path for path in (PAGES_DIR / folder).glob("*/index.html"))
    assert cards
    for card in cards:
        html = card.read_text(encoding="utf-8")
        [link] = _ROOT_LINK.findall(html)
        root_page = (card.parent / unquote(link) / "index.html").resolve()
        back = f'href="../../../{card.parent.relative_to(PAGES_DIR).as_posix()}/"'
        assert back in root_page.read_text(encoding="utf-8"), f"{card} is not on {root_page}"


@built
def test_every_built_verb_page_links_its_root_page_that_links_it_back():
    for language in ("bs", "en"):
        listing = (PAGES_DIR / language / "index.html").read_text(encoding="utf-8")
        for slug in re.findall(r'<li><a href="([^"/]+)/">', listing):
            html = (PAGES_DIR / language / slug / "index.html").read_text(encoding="utf-8")
            [link] = _ROOT_LINK.findall(html)
            root_page = (PAGES_DIR / language / slug / link / "index.html").resolve()
            assert f'href="../../../{language}/{slug}/"' in root_page.read_text(encoding="utf-8"), slug


@built
def test_the_root_pages_are_in_the_sitemap():
    sitemap = (PAGES_DIR / "sitemap.xml").read_text(encoding="utf-8")
    assert seo.absolute("bs/korijen/q-w-l/") in sitemap and seo.absolute("en/root/") in sitemap
    assert Path(PAGES_DIR / "en" / "root" / "q-w-l" / "index.html").is_file()
