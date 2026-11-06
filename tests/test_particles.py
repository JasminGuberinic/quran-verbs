"""Čestice / Particles: the Quran's most frequent small words.

The model refuses what must not reach a learner; the corpus reader finds every particle and
what the next word shows; the gate holds every count, cited ayah and claimed effect to the
corpus (golden: counts and moods from the QAC); the pages show the particle with its voice,
its uses, its ayat and the words of those ayat that have pages of their own.
"""

from __future__ import annotations

import shutil

import pytest

from fil import particle_store
from fil.corpus.parse import parse_segment
from fil.corpus.particles import iter_particle_occurrences, marker_after
from fil.languages import LANGUAGES
from fil.nouns.bosnian import renderings
from fil.particles import gate
from fil.particles.model import (KINDS, CorpusTag, InvalidParticleData, ParticleOccurrence, parse_particle,
                                 parse_particles)
from fil.pages import particle_render, render, seo
from fil.resources import QAC_MORPHOLOGY
from fil.stages.nuance_site import StudiedCards
from fil.stages.particle_site import StudiedWords, UnvoicedParticle, check_voiced
from fil.study import QuranWord

needs_corpus = pytest.mark.skipif(not QAC_MORPHOLOGY.exists(), reason="the corpus is not downloaded")
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _text(bs: str = "ne", en: str = "not") -> dict:
    return {"bs": bs, "en": en}


def _use(key: str = "did-not", **changes) -> dict:
    use = {"key": key, "kind": "negation", "tags": ["NEG"], "effect": "JUS", "title": _text(), "explanation": _text(),
           "ayat": [{"ref": "112:3:1", "why": _text()}]}
    return {**use, **changes}


def _entry(**changes) -> dict:
    entry = {"arabic": "لَمْ", "lemma": "لَم", "count": 348, "meaning": _text(), "grammar": _text(),
             "sources": ["Ibn Hišām, Muġnī al-labīb"], "uses": [_use()]}
    return {**entry, **changes}


# ---------------------------------------------------------------- the model refuses

def test_a_complete_particle_parses():
    particle = parse_particle("lam", _entry())
    use = particle.uses[0]
    assert particle.corpus_tags == (CorpusTag("NEG"),) and particle.kinds == ("negation",)
    assert use.effect == "JUS" and (use.ayat[0].surah, use.ayat[0].ayah, use.ayat[0].word) == (112, 3, 1)


@pytest.mark.parametrize(("slug", "entry", "complaint"), [
    ("Lam", _entry(), "slug"),
    ("lam", _entry(count=0), "count"),
    ("lam", _entry(uses=[]), "at least one use"),
    ("lam", _entry(uses=[_use(), _use()]), "same use twice"),
    ("lam", _entry(grammar={"bs": "x"}), "no en"),
    ("lam", _entry(sources=[]), "sources"),
    ("lam", _entry(uses=[_use(kind="adverb")]), "kind"),
    ("lam", _entry(uses=[_use(effect="DAT")]), "effect"),
    ("lam", _entry(uses=[_use(tags=[])]), "corpus tags"),
    ("lam", _entry(uses=[_use(tags=["NEG|إِنّ"])]), "not a corpus tag"),
    ("lam", _entry(uses=[_use(ayat=[])]), "cite 1–3"),
    ("lam", _entry(uses=[_use(ayat=[{"ref": f"2:{n}", "why": _text()} for n in range(1, 5)])]), "cite 1–3"),
    ("lam", _entry(uses=[_use(ayat=[{"ref": "112-3", "why": _text()}])]), "surah:ayah"),
    ("lam", _entry(uses=[_use(ayat=[{"ref": "112:3", "why": {"en": "x"}}])]), "no bs"),
    ("lam", _entry(preposition="an"), "preposition"),
    ("lam", _entry(spoken=" "), "spoken"),
])
def test_the_model_refuses_what_must_not_reach_a_learner(slug, entry, complaint):
    with pytest.raises(InvalidParticleData, match=complaint):
        parse_particle(slug, entry)


def test_two_particles_with_the_same_headword_are_refused():
    with pytest.raises(InvalidParticleData, match="same particle twice"):
        parse_particles({"lam": _entry(), "lam-2": _entry()})


def test_a_corpus_tag_reads_its_family():
    assert CorpusTag.parse("NEG|FAM:إِنّ") == CorpusTag("NEG", "إِنّ") and str(CorpusTag("NEG", "إِنّ")) == "NEG|FAM:إِنّ"
    assert CorpusTag.parse("P") == CorpusTag("P")


def test_a_proclitic_is_voiced_without_its_tatweel():
    assert parse_particle("bi", _entry(arabic="بِـ", lemma="ب")).said == "بِ"
    assert parse_particle("lam", _entry()).said == "لَمْ"


# ---------------------------------------------------------------- the corpus reader

def _segments(*lines: str):
    return [parse_segment(line) for line in lines]


def test_the_reader_finds_particles_and_function_nouns_but_not_the_article():
    found = list(iter_particle_occurrences(_segments(
        "2:3:6:1\tوَ\tP\tREM|PREF|LEM:و",
        "2:3:6:2\tمِ\tP\tP|LEM:مِن",
        "2:3:6:3\tمَّا\tN\tREL|LEM:ما",
        "2:3:7:1\tرَزَقْ\tV\tPERF|VF:1|ROOT:رزق|LEM:رَزَقَ|1P",
        "1:1:3:1\tٱل\tP\tDET|PREF|LEM:ال",
        "1:1:3:2\tرَّحْمَٰنِ\tN\tROOT:رحم|LEM:رَحْمٰن|MS|GEN|ADJ",
    )))
    assert [(occurrence.lemma, str(occurrence.corpus_tag)) for occurrence in found] == [
        ("و", "REM"), ("مِن", "P"), ("ما", "REL")]


@pytest.mark.parametrize(("following", "marker"), [
    (["1:2:2:2\tلَّهِ\tN\tPN|ROOT:أله|LEM:اللَّه|GEN"], "GEN"),
    (["1:1:3:1\tٱل\tP\tDET|PREF|LEM:ال", "1:1:3:2\tرَّحْمَٰنِ\tN\tROOT:رحم|LEM:رَحْمٰن|MS|GEN|ADJ"], "GEN"),   # article skipped
    (["112:3:2:1\tيَلِدْ\tV\tIMPF|VF:1|ROOT:ولد|LEM:وَلَدَ|3MS|MOOD:JUS"], "JUS"),
    (["2:2:5:2\tهِ\tN\tPRON|SUFF|3MS"], None),                                     # بِهِ: the pronoun shows nothing
    (["2:164:1:1\tفِى\tP\tP|LEM:فِي"], None),                                      # إِنَّ فِي: another particle first
    (["23:1:2:1\tأَفْلَحَ\tV\tPERF|VF:4|ROOT:فلح|LEM:أَفْلَحَ|3MS"], None),         # a past verb has no mood
])
def test_the_marker_is_what_the_next_inflected_word_shows(following, marker):
    assert marker_after(_segments(*following)) == marker


# ---------------------------------------------------------------- the gate

class _Concordance:
    def __init__(self, *occurrences: ParticleOccurrence) -> None:
        self.found = occurrences

    def occurrences(self, lemma: str, tag: CorpusTag):
        return [occurrence for occurrence in self.found if (occurrence.lemma, occurrence.corpus_tag) == (lemma, tag)]


def _lam(surah: int, ayah: int, word: int, marker: str | None = "JUS", tag: str = "NEG") -> ParticleOccurrence:
    return ParticleOccurrence("لَم", CorpusTag.parse(tag), surah, ayah, word, marker)


def _counted(occurrence: ParticleOccurrence, count: int) -> list[ParticleOccurrence]:
    """The cited occurrence and count − 1 others elsewhere."""
    return [occurrence, *(_lam(1, n, 1) for n in range(1, count))]


def test_the_gate_passes_what_the_corpus_bears_out():
    concordance = _Concordance(*_counted(_lam(112, 3, 1), 347), _lam(112, 3, 3))
    assert gate.problems([parse_particle("lam", _entry())], concordance) == []


def test_the_gate_refuses_a_wrong_count_a_missing_ayah_and_an_unknown_tag():
    particle = parse_particle("lam", _entry(count=5, uses=[_use(), _use("other", tags=["SUB"], effect=None)]))
    found = gate.problems([particle], _Concordance(_lam(2, 6, 8)))
    assert any("the corpus never files لَم as SUB" in problem for problem in found)
    assert any("the corpus counts 1, the data says 5" in problem for problem in found)
    assert any("112:3:1 does not hold لَمْ as NEG" in problem for problem in found)


def test_an_ayah_that_holds_the_use_twice_must_pin_the_word():
    particle = parse_particle("lam", _entry(count=2, uses=[_use(ayat=[{"ref": "112:3", "why": _text()}])]))
    found = gate.problems([particle], _Concordance(_lam(112, 3, 1), _lam(112, 3, 3)))
    assert found == ["lam did-not: 112:3 holds لَمْ as NEG at words [1, 3]: pin one (s:a:w)"]


def test_the_gate_refuses_an_effect_the_next_word_does_not_show():
    found = gate.problems([parse_particle("lam", _entry(count=1))], _Concordance(_lam(112, 3, 1, marker="IND")))
    assert found == ["lam did-not: at 112:3:1 the next word shows IND, not JUS"]


def test_a_use_is_counted_only_when_no_other_use_shares_its_tags():
    particle = parse_particle("ma", _entry(arabic="مَا", lemma="لَم", uses=[
        _use("not", effect=None), _use("relative", tags=["REL"], effect=None), _use("again", effect=None)]))
    concordance = _Concordance(_lam(1, 1, 1), _lam(1, 2, 1, tag="REL"), _lam(1, 3, 1, tag="REL"))
    assert gate.use_counts(particle, concordance) == {"not": None, "relative": 2, "again": None}


# ---------------------------------------------------------------- the stored particles, against the corpus

def test_the_stored_particles_load_and_every_text_is_bilingual():
    particles = particle_store.load_particles()
    assert len(particles) == 52 and particles[0].slug == "wa"
    assert [particle.count for particle in particles] == sorted((particle.count for particle in particles), reverse=True)
    assert all(particle.sources and particle.uses for particle in particles)


@pytest.fixture(scope="module")
def corpus():
    from fil.stages.particles import CorpusParticleConcordance
    return CorpusParticleConcordance.from_corpus()


@needs_corpus
def test_every_stored_particle_passes_the_corpus_gate(corpus):
    assert gate.problems(particle_store.load_particles(), corpus) == []


@needs_corpus
@pytest.mark.parametrize(("lemma", "tag", "count"), [
    ("مِن", "P", 3226), ("فِي", "P", 1701), ("ب", "P", 2544), ("لَم", "NEG", 348), ("لَن", "NEG", 106),
    ("إِنّ", "ACC|FAM:إِنّ", 1682), ("لا", "PRO", 332), ("لا", "NEG|FAM:إِنّ", 57), ("ما", "REL", 1475),
    ("ل", "EMPH", 1001), ("أ", "INTG", 507), ("ي", "VOC", 361), ("مَن", "COND", 184), ("س", "FUT", 119),
])
def test_golden_counts_come_from_the_corpus(corpus, lemma, tag, count):
    assert len(corpus.occurrences(lemma, CorpusTag.parse(tag))) == count


@needs_corpus
@pytest.mark.parametrize(("lemma", "tag", "mood", "share"), [
    ("لَم", "NEG", "JUS", 0.99),        # 345 of 348
    ("لَن", "NEG", "SUBJ", 1.0),
    ("ل", "IMPV", "JUS", 1.0),
    ("ل", "PRP", "SUBJ", 0.98),
    ("س", "FUT", "IND", 0.98),          # 117 of 119
    ("سَوْف", "FUT", "IND", 0.97),       # 41 of 42
    ("لَمّا", "NEG", "JUS", 0.87),       # 7 of 8 (62:3 is tagged SUBJ)
])
def test_what_the_grammar_says_a_particle_does_holds_across_the_corpus(corpus, lemma, tag, mood, share):
    found = corpus.occurrences(lemma, CorpusTag.parse(tag))
    assert sum(occurrence.marker == mood for occurrence in found) / len(found) >= share


# ---------------------------------------------------------------- cards

def test_a_preposition_is_rendered_in_bosnian_as_the_noun_glosses_render_it():
    assert renderings("fi") == (("u", "L"), ("na", "L"))
    assert renderings("bi") == (("", "I"), ("s", "I"))
    assert renderings("min") == (("iz", "G"), ("od", "G"))


def test_the_words_of_an_ayah_link_the_cards_we_teach_once_each():
    studied = StudiedWords.of(verb_locations={"قول_1": [(2, 8, 4)]},
                              lemma_locations={"نَاس|نوس": [(2, 8, 2), (2, 8, 9)], "يَوْم|يوم": [(2, 8, 7)]},
                              studied=StudiedCards(verbs={"قول_1": "qala"}, nouns={"نَاس|نوس": "nas"}, adjectives={}))
    words = [QuranWord(2, 8, number, text) for number, text in
             enumerate(["وَمِنَ", "ٱلنَّاسِ", "مَن", "يَقُولُ", "ءَامَنَّا", "بِٱللَّهِ", "وَبِٱلْيَوْمِ", "ٱلْءَاخِرِ", "ٱلنَّاسُ"], 1)]
    assert studied.in_ayah(2, 8, words) == [{"text": "ٱلنَّاسِ", "kind": "noun", "slug": "nas"},
                                            {"text": "يَقُولُ", "kind": "verb", "slug": "qala"}]


def _card(**changes) -> dict:
    ayah = {"ref": "26:147", "audio": "https://stream/26147.mp3", "why": _text("U vrtovima", "In gardens"),
            "translation": {"en": {"text": "In gardens and watersprings", "by": "Pickthall"}},
            "words": [{"text": "فِى", "hit": True, "audio": "audio/w.m4a"}, {"text": "جَنَّٰتٍ", "hit": False}],
            "studied": [{"text": "جَنَّٰتٍ", "kind": "noun", "slug": "janna"}]}
    use = {"key": "place", "kind": "preposition", "title": _text("„u“: mjesto", "“in”: place"),
           "explanation": _text("Mjesto: فِي", "Place"), "effect": "GEN", "count": None, "ayat": [ayah]}
    card = {"slug": "fi", "arabic": "فِي", "audio": "audio/f.m4a", "count": 1701, "meaning": _text("u, na", "in"),
            "grammar": _text("Prijedlog.", "A preposition."), "kinds": ["preposition"],
            "preposition": [{"word": "u", "case": "L"}, {"word": "na", "case": "L"}],
            "caseNoun": {"text": "جَنَّٰتٍ", "kind": "noun", "slug": "janna"}, "uses": [use], "sources": ["Ibn Hišām"],
            "unvoiced": []}
    return {**card, **changes}


def test_a_silent_headword_stops_the_build_unless_documented():
    check_voiced([_card()], {})
    check_voiced([_card(unvoiced=["فِي"])], {"فِي": "documented"})
    with pytest.raises(UnvoicedParticle):
        check_voiced([_card(unvoiced=["فِي"])], {})


# ---------------------------------------------------------------- pages

@pytest.fixture(scope="module")
def texts():
    from fil.pages import interface_text
    return interface_text.load()


@needs_node
def test_every_kind_of_use_is_named_in_both_languages_of_the_section(texts):
    for code in particle_render.PARTICLE_LANGUAGES:
        assert set(KINDS) <= set(texts[code]["particlePage"]["kinds"]), code


def _language(code: str):
    return next(language for language in LANGUAGES if language.code == code)


@needs_node
def test_a_particle_page_shows_what_it_does_its_uses_and_their_ayat(texts):
    html = particle_render.particle_page(_card(), _language("bs"), texts["bs"], published={render.NOUNS})
    assert '<span class="ar lemma" lang="ar" dir="rtl">فِي</span>' in html and "1701× u Kur&#x27;anu" in html
    assert 'data-audio="../../../audio/f.m4a"' in html                       # the headword's voice
    assert '<mark data-audio="../../../audio/w.m4a"' in html                 # the particle in the ayah, recited
    assert "u + lokativ · na + lokativ" in html                               # as the noun glosses render it
    assert "Imenica iza je u genitivu." in html and "prijedlog" in html
    assert 'href="../../../bs/imenica/janna/#cases"' in html                  # the cases, on a noun page
    assert 'href="../../../bs/imenica/janna/"' in html                        # a studied word of the ayah
    assert 'hreflang="en" href="https://jasminguberinic.github.io/quran-verbs/en/particle/fi/"' in html


@needs_node
def test_an_english_page_says_nothing_of_bosnian_and_links_no_unpublished_section(texts):
    html = particle_render.particle_page(_card(), _language("en"), texts["en"], published=())
    assert "lokativ" not in html and "#cases" not in html and "noun/janna" not in html
    assert "The noun after it is genitive." in html


@needs_node
def test_the_list_of_particles_links_every_particle(texts):
    html = particle_render.particle_index([_card(), _card(slug="min", arabic="مِنْ")], _language("en"), texts["en"],
                                          published=())
    assert 'href="fi/"' in html and 'href="min/"' in html and "Particles: the small words" in html


@needs_node
@pytest.mark.parametrize("code", [language.code for language in LANGUAGES])
def test_the_top_bar_leads_to_the_particles_only_in_bosnian_and_english(texts, code):
    bar = render.top_bar(texts[code], "../", _language(code), "", section=render.VERBS, published={render.PARTICLES})
    assert (f'href="../{code}/{seo.PARTICLE_FOLDERS.get(code)}/"' in bar) == (code in seo.PARTICLE_FOLDERS)
