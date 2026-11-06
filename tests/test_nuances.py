"""Nijanse / Nuances: groups of Quranic near-synonyms.

The model refuses what must not reach a learner; the gate holds every count and cited ayah
to the corpus (golden: the pilot's counts, from the QAC catalogues); the pages show each
word with its voice, its card link and its ayat, and the cards link back to their group.
"""

from __future__ import annotations

import copy
import shutil

import pytest

from fil import nuance_store
from fil.languages import LANGUAGES
from fil.nuances import gate
from fil.nuances.gate import Attestation
from fil.nuances.model import CorpusWord, InvalidNuanceData, parse_group, parse_groups
from fil.pages import nuance_render, render, seo
from fil.resources import QAC_MORPHOLOGY
from fil.stages.nuance_site import (StudiedCards, UnvoicedNuanceText, check_voiced, groups_of_lemma,
                                    groups_of_verb)

needs_corpus = pytest.mark.skipif(not QAC_MORPHOLOGY.exists(), reason="the corpus is not downloaded")
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _text(bs: str = "srce", en: str = "heart") -> dict:
    return {"bs": bs, "en": en}


def _member(arabic: str = "قَلْب", **changes) -> dict:
    member = {"arabic": arabic, "lemmas": ["قَلْب|قلب"], "count": 132, "meaning": _text(), "nuance": _text(),
              "ayat": [{"ref": "22:46", "why": _text()}]}
    return {**member, **changes}


def _entry(**changes) -> dict:
    entry = {"title": _text(), "shared": _text(), "tellApart": _text(), "sources": ["ar-Rāġib, Mufradāt"],
             "verified": [{"source": "0502RaghibIsbahani.Mufradat.JK001150-ara1", "entries": ["قلب", "فأد"]}],
             "members": [_member(), _member("فُؤَاد", lemmas=["فُؤاد|فأد"], count=16,
                                            ayat=[{"ref": "28:10", "why": _text()}])]}
    return {**entry, **changes}


# ---------------------------------------------------------------- the model refuses

def test_a_complete_group_parses():
    group = parse_group("qalb-fuad", _entry())
    assert [member.arabic for member in group.members] == ["قَلْب", "فُؤَاد"]
    assert group.members[0].corpus.lemmas == (("قَلْب", "قلب"),)
    assert group.members[1].ayat[0].reference == "28:10"


@pytest.mark.parametrize(("slug", "entry", "complaint"), [
    ("Qalb", _entry(), "slug"),
    ("qalb", _entry(members=[_member()]), "at least 2 members"),
    ("qalb", _entry(shared={"bs": "srce"}), "no en"),
    ("qalb", _entry(title={"bs": " ", "en": "heart"}), "no bs"),
    ("qalb", _entry(sources=[]), "sources"),
    ("qalb", _entry(members=[_member(), _member()]), "same member twice"),
    ("qalb", _entry(members=[_member(count=0), _member("فُؤَاد")]), "count"),
    ("qalb", _entry(members=[_member(ayat=[]), _member("فُؤَاد")]), "cite 1–3"),
    ("qalb", _entry(members=[_member(ayat=[{"ref": f"2:{n}", "why": _text()} for n in range(1, 5)]),
                             _member("فُؤَاد")]), "cite 1–3"),
    ("qalb", _entry(members=[_member(ayat=[{"ref": "22-46", "why": _text()}]), _member("فُؤَاد")]), "surah:ayah"),
    ("qalb", _entry(members=[_member(ayat=[{"ref": "22:46", "why": {"en": "x"}}]), _member("فُؤَاد")]), "no bs"),
    ("qalb", _entry(members=[_member(verb="قلب_1"), _member("فُؤَاد")]), "exactly one of"),
    ("qalb", _entry(members=[_member(lemmas=None, verb="قلب"), _member("فُؤَاد")]), "root_form"),
    ("qalb", _entry(members=[_member(lemmas=["قَلْب"]), _member("فُؤَاد")]), "lemma|root"),
    ("qalb", _entry(verified=[{"entries": ["قلب"]}]), "source"),
    ("qalb", _entry(verified=[{"source": "0502RaghibIsbahani.Mufradat.JK001150-ara1", "entries": []}]), "entries"),
    ("qalb", _entry(verified=[{"source": "0502RaghibIsbahani.Mufradat.JK001150-ara1", "entries": ["قلب", "قلب"]}]),
     "same entry twice"),
])
def test_the_model_refuses_what_must_not_reach_a_learner(slug, entry, complaint):
    with pytest.raises(InvalidNuanceData, match=complaint):
        parse_group(slug, entry)


def test_a_headword_is_voiced_as_shown_unless_a_spoken_form_is_given():
    plain, pausal = parse_group("g", _entry(members=[_member(), _member("خَشْيَة", spoken="خَشْيَةٌ")])).members
    assert plain.said == "قَلْب" and pausal.said == "خَشْيَةٌ"
    with pytest.raises(InvalidNuanceData, match="spoken"):
        parse_group("g", _entry(members=[_member(), _member("خَشْيَة", spoken=" ")]))


def test_a_verb_member_is_known_by_its_root_and_form():
    word = parse_group("jaa", _entry(members=[_member("جَاءَ", lemmas=None, verb="جيأ_1"), _member()])).members[0].corpus
    assert word.is_verb and word.verb == ("جيأ", 1) and word.verb_key == "جيأ_1" and word.lemma_keys == ()


def test_the_stored_groups_load_and_every_text_is_bilingual():
    groups = nuance_store.load_groups()
    assert [group.slug for group in groups][:5] == ["insan-bashar", "jaa-ata", "raa-nazara-absara", "khawf-khashya",
                                                    "qalb-fuad-sadr"]
    assert len(groups) == 230 and len({group.slug for group in groups}) == 230
    assert all(len(group.members) >= 2 and group.sources for group in groups)


# ---------------------------------------------------------------- the corpus gate

class _Concordance:
    def __init__(self, known: dict[str, Attestation]) -> None:
        self.known = known

    def attestation(self, word: CorpusWord) -> Attestation | None:
        return self.known.get(word.describe())


def _attested(count: int, *locations: tuple[int, int, int]) -> Attestation:
    return Attestation(count, frozenset(locations))


def test_the_gate_passes_what_the_corpus_bears_out():
    groups = parse_groups({"qalb": _entry()})
    concordance = _Concordance({"قَلْب|قلب": _attested(132, (22, 46, 14)), "فُؤاد|فأد": _attested(16, (28, 10, 2))})
    assert gate.problems(groups, concordance) == []


def test_the_gate_refuses_a_wrong_count_a_wrong_ayah_and_an_unknown_word():
    groups = parse_groups({"qalb": _entry()})
    concordance = _Concordance({"قَلْب|قلب": _attested(131, (2, 7, 3))})
    found = gate.problems(groups, concordance)
    assert any("the corpus counts 131, the data says 132" in problem for problem in found)
    assert any("22:46 does not hold this word" in problem for problem in found)
    assert any("فُؤَاد" in problem and "not a word of the corpus" in problem for problem in found)


def test_the_gate_refuses_words_put_in_ar_raghibs_mouth_unchecked():
    concordance = _Concordance({"قَلْب|قلب": _attested(132, (22, 46, 14)), "فُؤاد|فأد": _attested(16, (28, 10, 2))})
    unchecked = parse_groups({"qalb": _entry(verified=[])})
    assert gate.problems(unchecked, concordance) == [
        "qalb: speaks in ar-Rāġib's name but records no check against the Mufradāt "
        "(`verified`: 0502RaghibIsbahani.Mufradat…, `fil nuances mufradat ROOT`)"]
    unattributed = parse_groups({"qalb": _entry(verified=[], sources=["Quranic usage — our own observation"])})
    assert gate.problems(unattributed, concordance) == []


def test_the_gate_wants_the_cited_entries_spelled_as_the_ones_read():
    concordance = _Concordance({"قَلْب|قلب": _attested(132, (22, 46, 14)), "فُؤاد|فأد": _attested(16, (28, 10, 2))})
    as_read = parse_groups({"qalb": _entry(sources=["ar-Rāġib al-Iṣfahānī, Mufradāt — entries قلب, فأد"])})
    assert gate.problems(as_read, concordance) == []
    misspelled = parse_groups({"qalb": _entry(sources=["ar-Rāġib al-Iṣfahānī, Mufradāt — entries قلب, فؤاد"])})
    assert gate.problems(misspelled, concordance) == [
        "qalb: its sources cite the Mufradāt entry فؤاد, which `verified` does not list "
        "(name the entries read, spelled as the book does)"]


def test_an_attestation_knows_the_words_of_an_ayah():
    attestation = _attested(3, (22, 46, 7), (22, 46, 14), (2, 7, 3))
    assert attestation.words_in(22, 46) == {7, 14} and attestation.places == {(22, 46), (2, 7)}


@pytest.fixture(scope="module")
def concordance():
    from fil.stages.nuances import CatalogueConcordance
    return CatalogueConcordance.from_corpus()


@needs_corpus
def test_every_stored_group_passes_the_corpus_gate(concordance):
    assert gate.problems(nuance_store.load_groups(), concordance) == []


@needs_corpus
@pytest.mark.parametrize(("word", "count"), [
    (CorpusWord(lemmas=(("ناس", "أنس"),)), 241),
    (CorpusWord(lemmas=(("إِنسان", "أنس"),)), 71),
    (CorpusWord(lemmas=(("رَجُل", "رجل"), ("رِجال", "رجل"))), 57),          # the broken plural is a lemma of its own
    (CorpusWord(lemmas=(("امْرِئ", "مرأ"), ("مَرْء", "مرأ"), ("امْرُؤٌا", "مرأ"), ("امْرَأ", "مرأ"))), 11),
    (CorpusWord(verb=("جيأ", 1)), 278),
    (CorpusWord(verb=("أتي", 1)), 264),                                       # not Form IV آتَى "to give"
    (CorpusWord(verb=("بصر", 4)), 29),
    (CorpusWord(lemmas=(("خَشْيَة", "خشي"),)), 8),
    (CorpusWord(lemmas=(("قَلْب", "قلب"),)), 132),
])
def test_golden_counts_come_from_the_catalogues(concordance, word, count):
    assert concordance.attestation(word).count == count


@needs_corpus
def test_7_198_holds_both_looking_and_seeing(concordance):
    looking = concordance.attestation(CorpusWord(verb=("نظر", 1)))
    seeing = concordance.attestation(CorpusWord(verb=("بصر", 4)))
    assert (7, 198) in looking.places and (7, 198) in seeing.places


@needs_corpus
def test_an_unknown_lemma_is_not_a_word_of_the_corpus(concordance):
    assert concordance.attestation(CorpusWord(lemmas=(("قَلْب", "قلب"), ("قلبون", "قلب")))) is None


# ---------------------------------------------------------------- cards and the voice gate

def _group_card(slug: str = "qalb-fuad", **member_changes) -> dict:
    member = {"arabic": "قَلْب", "audio": "audio/q.m4a", "count": 132, "meaning": _text(), "nuance": _text("Srce je قَلْب.", "The heart."),
              "verbKey": None, "lemmaKeys": ["قَلْب|قلب"], "card": {"kind": "noun", "slug": "qalb"},
              "ayat": [{"ref": "22:46", "audio": "https://stream/22046.mp3", "why": _text("Zašto", "Why"),
                        "translation": {"en": {"text": "Have they not travelled", "by": "Pickthall"}},
                        "words": [{"text": "أَفَلَمْ", "hit": False},
                                  {"text": "ٱلْقُلُوبُ", "hit": True, "audio": "audio/w.m4a"}]}],
              **member_changes}
    other = {**copy.deepcopy(member), "arabic": "صَدْر", "lemmaKeys": ["صَدْر|صدر"], "card": None}
    return {"slug": slug, "title": _text("Srce", "Heart"), "shared": _text(), "tellApart": _text("قَلْب ili صَدْر", "x"),
            "sources": ["ar-Rāġib"], "members": [member, other], "unvoiced": []}


def test_a_silent_headword_stops_the_build_unless_documented():
    silent = {**_group_card(), "unvoiced": ["قَلْب"]}
    check_voiced([_group_card()], {})
    check_voiced([silent], {"قَلْب": "documented"})
    with pytest.raises(UnvoicedNuanceText):
        check_voiced([silent], {})


def test_a_card_finds_the_groups_its_word_belongs_to():
    cards = [_group_card(), _group_card("jaa", verbKey="جيأ_1", lemmaKeys=[])]
    assert [card["slug"] for card in groups_of_lemma("قَلْب|قلب", cards)] == ["qalb-fuad"]
    assert [card["slug"] for card in groups_of_verb("جيأ_1", cards)] == ["jaa"]
    assert groups_of_lemma("بَيْت|بيت", cards) == []


def test_a_member_links_the_card_we_teach_for_it():
    studied = StudiedCards(verbs={"جيأ_1": "jaa"}, nouns={"قَلْب|قلب": "qalb"}, adjectives={"كَبِير|كبر": "kabir"})
    verb, noun, untaught = parse_group("g", _entry(members=[
        _member("جَاءَ", lemmas=None, verb="جيأ_1"), _member(), _member("صَدْر", lemmas=["صَدْر|صدر"])])).members
    assert studied.card_of(verb) == {"kind": "verb", "slug": "jaa"}
    assert studied.card_of(noun) == {"kind": "noun", "slug": "qalb"}
    assert studied.card_of(untaught) is None


# ---------------------------------------------------------------- pages

@pytest.fixture(scope="module")
def texts():
    from fil.pages import interface_text
    return interface_text.load()


def _language(code: str):
    return next(language for language in LANGUAGES if language.code == code)


@needs_node
def test_a_group_page_shows_each_word_its_voice_its_card_and_its_ayat(texts):
    html = nuance_render.nuance_page(_group_card(), _language("bs"), texts["bs"],
                                     published={render.NOUNS, render.ADJECTIVES})
    assert "<h1>Srce</h1>" in html and "Kako ih razlikovati" in html and "Zašto ova riječ ovdje" in html
    assert 'data-audio="../../../audio/q.m4a"' in html                       # the headword's voice
    assert '<mark data-audio="../../../audio/w.m4a"' in html                 # the word in the ayah, recited
    assert 'href="../../../bs/imenica/qalb/"' in html and "Stranica imenice" in html
    assert '<span class="ar notranslate" lang="ar" dir="rtl" translate="no">قَلْب</span>' in html       # Arabic inside a Bosnian text
    assert 'hreflang="en" href="https://jasminguberinic.github.io/quran-verbs/en/nuances/qalb-fuad/"' in html
    assert html.count("Nijanse") >= 2                                        # top bar and eyebrow


@needs_node
def test_the_list_of_groups_links_every_group(texts):
    html = nuance_render.nuance_index([_group_card(), _group_card("jaa")], _language("en"), texts["en"],
                                      published=())
    assert 'href="qalb-fuad/"' in html and 'href="jaa/"' in html and "Nuances: near-synonyms" in html


@needs_node
def test_similar_words_link_the_group_only_where_nuance_pages_exist(texts):
    section = nuance_render.similar_words_section([_group_card()], _language("bs"), texts["bs"], "../../")
    assert "Slične riječi" in section and 'href="../../bs/nijanse/qalb-fuad/"' in section
    assert nuance_render.similar_words_section([_group_card()], _language("tr"), texts["tr"], "../") == ""
    assert nuance_render.similar_words_section([], _language("en"), texts["en"], "../") == ""


@needs_node
@pytest.mark.parametrize("code", [language.code for language in LANGUAGES])
def test_the_top_bar_leads_to_the_nuances_only_in_bosnian_and_english(texts, code):
    bar = render.top_bar(texts[code], "../", _language(code), seo.language_index_path, section=render.VERBS,
                         published={render.NOUNS, render.ADJECTIVES, render.NUANCES})
    assert (f'href="../{code}/{seo.NUANCE_FOLDERS.get(code)}/"' in bar) == (code in seo.NUANCE_FOLDERS)
