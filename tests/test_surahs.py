"""Sure / Surahs: the vocabulary of a surah and how much of it the site teaches (docs/SURAHS-PLAN.md).

Golden: al-Ikhlāṣ as the corpus segments it — 15 words, each under the headword a learner looks up.
Structural: every token of every surah is in exactly one entry (the gate), on the corpus itself and
on the built pages. The pages: what a row shows, what it links, what it keeps out.
"""

from __future__ import annotations

import gzip
import re
from html.parser import HTMLParser

import pytest

from fil.corpus.parse import iter_segments
from fil.languages import LANGUAGES
from fil.pages import render, seo, surah_render
from fil.pages.exercise_render import MAX_SURAH_WORDS, words_practice_link
from fil.pages.interface_text import load as load_texts
from fil.quran_numbering import SURAH_AYAH_COUNTS
from fil.resources import PAGES_DIR, QAC_MORPHOLOGY
from fil.surah_store import load_surahs
from fil.surahs.headword import headword_of, tokens_of
from fil.surahs.model import NOUN, OTHER, PARTICLE, PRONOUN, VERB, Headword, InvalidSurahData, Surah, Taught, name_slug
from fil.surahs.vocabulary import SurahNotAccountedFor, by_frequency, problems, vocabulary_of

# Surah 112 as the Quranic Arabic Corpus segments it (GNU GPL, corpus.quran.com), verbatim.
AL_IKHLAS = """\
112:1:1:1\tقُلْ\tV\tIMPV|VF:1|ROOT:قول|LEM:قالَ|2MS
112:1:2:1\tهُوَ\tN\tPRON|3MS
112:1:3:1\tٱللَّهُ\tN\tPN|ROOT:أله|LEM:اللَّه|NOM
112:1:4:1\tأَحَدٌ\tN\tROOT:أحد|LEM:أَحَد|M|INDEF|NOM
112:2:1:1\tٱللَّهُ\tN\tPN|ROOT:أله|LEM:اللَّه|NOM
112:2:2:1\tٱل\tP\tDET|PREF|LEM:ال
112:2:2:2\tصَّمَدُ\tN\tROOT:صمد|LEM:صَمَد|MS|NOM
112:3:1:1\tلَمْ\tP\tNEG|LEM:لَم
112:3:2:1\tيَلِدْ\tV\tIMPF|VF:1|ROOT:ولد|LEM:وَلَدَ|3MS|MOOD:JUS
112:3:3:1\tوَ\tP\tCONJ|PREF|LEM:و
112:3:3:2\tلَمْ\tP\tNEG|LEM:لَم
112:3:4:1\tيُولَدْ\tV\tIMPF|VF:1|PASS|ROOT:ولد|LEM:وَلَدَ|3MS|MOOD:JUS
112:4:1:1\tوَ\tP\tCONJ|PREF|LEM:و
112:4:1:2\tلَمْ\tP\tNEG|LEM:لَم
112:4:2:1\tيَكُن\tV\tIMPF|VF:1|ROOT:كون|LEM:كانَ|FAM:كَان|3MS|MOOD:JUS
112:4:3:1\tلَّ\tP\tP|PREF|LEM:ل
112:4:3:2\tهُۥ\tN\tPRON|3MS
112:4:4:1\tكُفُوًا\tN\tROOT:كفأ|LEM:كُفُو|M|INDEF|ACC
112:4:5:1\tأَحَدٌۢ\tN\tROOT:أحد|LEM:أَحَد|M|INDEF|NOM
"""
# 2:2 ذَٰلِكَ ٱلْكِتَٰبُ لَا رَيْبَ فِيهِ هُدًى, and three words of other ayat a headword is decided on.
OTHER_WORDS = """\
2:2:1:1\tذَٰ\tN\tDEM|LEM:ذا|MS
2:2:1:2\tلِ\tP\tDIST|SUFF|LEM:ل
2:2:1:3\tكَ\tP\tADDR|SUFF|M
2:2:5:1\tفِي\tP\tP|LEM:فِي
2:2:5:2\tهِ\tN\tPRON|SUFF|3MS
2:11:1:1\tوَ\tP\tCONJ|PREF|LEM:و
2:11:1:2\tإِذَا\tN\tT|LEM:إِذا
2:177:1:1\tلَّيْسَ\tV\tPERF|ROOT:ليس|LEM:لَيْسَ|FAM:كَان|3MS
2:11:6:1\tقَالُوٓا۟\tV\tPERF|VF:1|ROOT:قول|LEM:قالَ|3MP
"""
IKHLAS = Surah(112, "الإخلاص", "Al-Ikhlaas", "Sincerity", "meccan", 4)

# What the site teaches of al-Ikhlāṣ (as the cards key it) — al-ṣamad, kufuw and the Name are not cards.
TAUGHT = {
    (VERB, "قول_1"): Taught("verb", "qala", "قالَ", {"bs": "reći", "en": "to say"}, "قول"),
    (VERB, "ولد_1"): Taught("verb", "walada", "وَلَدَ", {"bs": "roditi", "en": "to beget"}, "ولد"),
    (VERB, "كون_1"): Taught("verb", "kana", "كانَ", {"bs": "biti", "en": "to be"}, "كون"),
    (NOUN, "أَحَد|أحد"): Taught("noun", "ahad", "أَحَد", {"bs": "jedan", "en": "one"}, "أحد"),
    (PARTICLE, "لَم|NEG"): Taught("particle", "lam", "لَمْ", {"bs": "ne", "en": "not"}),
    (PARTICLE, "ل|P"): Taught("particle", "li", "لِـ", {"bs": "za", "en": "for"}),
    (PRONOUN, "هُوَ|PRON"): Taught("pronoun", "huwa", "هُوَ", {"bs": "on", "en": "he"}),
}


def teach(headword: Headword) -> Taught | None:
    return TAUGHT.get((headword.kind, headword.key))


def _tokens(lines: str, verb_keys=None):
    return tokens_of(iter_segments(iter(lines.splitlines(keepends=True))), verb_keys or {})


def _words(lines: str) -> dict[tuple[int, int, int], list]:
    found: dict = {}
    for segment in iter_segments(iter(lines.splitlines(keepends=True))):
        found.setdefault((segment.surah, segment.ayah, segment.word), []).append(segment)
    return found


# ---------------------------------------------------------------- golden: al-Ikhlāṣ

def test_al_ikhlas_has_fifteen_words_each_headed_as_a_learner_looks_it_up():
    tokens = _tokens(AL_IKHLAS)
    assert len(tokens) == 15
    assert [(token.headword.kind, token.headword.key) for token in tokens] == [
        (VERB, "قول_1"), (PRONOUN, "هُوَ|PRON"), (NOUN, "اللَّه|أله"), (NOUN, "أَحَد|أحد"),
        (NOUN, "اللَّه|أله"), (NOUN, "صَمَد|صمد"),
        (PARTICLE, "لَم|NEG"), (VERB, "ولد_1"), (PARTICLE, "لَم|NEG"), (VERB, "ولد_1"),
        (PARTICLE, "لَم|NEG"), (VERB, "كون_1"), (PARTICLE, "ل|P"), (NOUN, "كُفُو|كفأ"), (NOUN, "أَحَد|أحد"),
    ]
    assert [token.text for token in tokens][8] == "وَلَمْ"


def test_al_ikhlas_coverage_counts_its_tokens_not_its_words():
    vocabulary = vocabulary_of(IKHLAS, _tokens(AL_IKHLAS), teach)
    # قُلْ هُوَ أَحَدٌ لَمْ يَلِدْ وَلَمْ يُولَدْ وَلَمْ يَكُن لَّهُۥ أَحَدٌۢ: 11 of 15 (ٱللَّهُ ×2, ٱلصَّمَدُ, كُفُوًا are not cards).
    assert (vocabulary.covered, len(vocabulary.tokens), vocabulary.coverage_percent) == (11, 15, 73)
    assert [entry.key for entry in vocabulary.entries] == [
        "verb:qala", "pronoun:huwa", "noun:اللَّه|أله", "noun:ahad", "noun:صَمَد|صمد", "particle:lam", "verb:walada",
        "verb:kana", "particle:li", "noun:كُفُو|كفأ"]
    lam = next(entry for entry in vocabulary.entries if entry.key == "particle:lam")
    assert lam.count == 3 and lam.forms == (("لَمْ", 1), ("وَلَمْ", 2)) and lam.first.location == (112, 3, 1)
    walada = next(entry for entry in vocabulary.entries if entry.key == "verb:walada")
    assert walada.forms == (("يَلِدْ", 1), ("يُولَدْ", 1))   # the passive is the same verb, and counted
    assert [entry.key for entry in vocabulary.untaught] == ["noun:اللَّه|أله", "noun:صَمَد|صمد", "noun:كُفُو|كفأ"]


def test_by_frequency_puts_the_commonest_first_and_keeps_the_surahs_order_among_equals():
    vocabulary = vocabulary_of(IKHLAS, _tokens(AL_IKHLAS), teach)
    assert [entry.key for entry in by_frequency(vocabulary.entries)][:4] == [
        "particle:lam", "noun:اللَّه|أله", "noun:ahad", "verb:walada"]


def test_coverage_is_rounded_down_never_up():
    vocabulary = vocabulary_of(IKHLAS, _tokens(AL_IKHLAS), lambda headword: None if headword.kind == NOUN else teach(headword))
    assert vocabulary.covered == 9 and vocabulary.coverage_percent == 60
    everything = vocabulary_of(IKHLAS, _tokens(AL_IKHLAS), lambda headword: Taught("noun", headword.key, "x", {}))
    assert everything.coverage_percent == 100


# ---------------------------------------------------------------- headwords

def test_a_headword_is_the_most_lexical_part_of_the_word():
    words = _words(OTHER_WORDS)
    assert headword_of(words[(2, 2, 1)]) == Headword(PRONOUN, "ذَٰلِكَ|DEM", "ذَٰلِكَ")   # the far demonstrative, named
    assert headword_of(words[(2, 2, 5)]) == Headword(PARTICLE, "فِي|P", "فِي")       # not its suffixed ـهِ
    assert headword_of(words[(2, 11, 1)]) == Headword(PARTICLE, "إِذا|T", "إِذا")     # the stem, not the وَ before it
    assert headword_of(words[(2, 177, 1)]) == Headword(PARTICLE, "لَيْسَ|V|FAM:كَان", "لَيْسَ")   # a verb the particles teach
    assert headword_of(words[(2, 11, 6)]).key == "قول_1"


def test_the_corrected_catalogue_decides_a_verbs_key():
    word = _words(OTHER_WORDS)[(2, 11, 6)]
    assert headword_of(word, verb_key="غني_4").key == "غني_4"


def test_a_particle_entry_gathers_its_uses_only_when_no_card_teaches_them():
    negating = Headword(PARTICLE, "ما|NEG", "ما")
    relative = Headword(PARTICLE, "ما|REL", "ما")
    assert negating.group == relative.group == "particle:ما"


# ---------------------------------------------------------------- the gate

def test_a_surah_missing_a_word_is_refused():
    tokens = [token for token in _tokens(AL_IKHLAS) if token.location != (112, 1, 2)]
    with pytest.raises(SurahNotAccountedFor, match=r"112:1: words 1…4 \(3\), not 1–3"):
        vocabulary_of(IKHLAS, tokens, teach)


def test_a_surah_missing_an_ayah_or_holding_anothers_word_is_refused():
    tokens = _tokens(AL_IKHLAS)
    with pytest.raises(SurahNotAccountedFor, match="not 1–4"):
        vocabulary_of(IKHLAS, [token for token in tokens if token.ayah != 4], teach)
    with pytest.raises(SurahNotAccountedFor, match="not in surah 112"):
        vocabulary_of(IKHLAS, [*tokens, *_tokens(OTHER_WORDS)[:1]], teach)


def test_the_gate_finds_a_token_counted_twice():
    vocabulary = vocabulary_of(IKHLAS, _tokens(AL_IKHLAS), teach)
    first = vocabulary.entries[0]
    doubled = type(vocabulary)(vocabulary.surah, vocabulary.tokens,
                               (*vocabulary.entries, type(first)(first.headword, None, first.tokens)))
    found = problems(doubled)
    assert any("112:1:1 is in 2 entries" in problem for problem in found)
    assert any("the entries count 16 tokens" in problem for problem in found)


@pytest.mark.skipif(not QAC_MORPHOLOGY.is_file(), reason="the corpus is not downloaded (data/qac)")
def test_every_token_of_every_surah_is_accounted_for():
    with QAC_MORPHOLOGY.open(encoding="utf-8") as lines:
        tokens = tokens_of(iter_segments(lines), {})
    surahs = load_surahs()
    total = 0
    for surah in surahs:
        vocabulary = vocabulary_of(surah, [token for token in tokens if token.surah == surah.number], lambda _h: None)
        total += sum(entry.count for entry in vocabulary.entries)
    assert total == len(tokens) == 77_429
    assert sum(1 for token in tokens if token.headword.kind == OTHER) < 0.02 * len(tokens)


# ---------------------------------------------------------------- the surahs' data

def test_the_surahs_are_the_114_of_the_numbering_with_stable_page_names():
    surahs = load_surahs()
    assert [surah.ayah_count for surah in surahs] == list(SURAH_AYAH_COUNTS)
    slugs = {surah.number: surah.slug for surah in surahs}
    assert [slugs[number] for number in (1, 2, 3, 18, 36, 67, 112, 114)] == [
        "1-al-fatiha", "2-al-baqara", "3-al-i-imran", "18-al-kahf", "36-yasin", "67-al-mulk", "112-al-ikhlas", "114-an-nas"]
    assert {surah.revelation for surah in surahs} == {"meccan", "medinan"}
    assert surahs[1].revelation == "medinan" and surahs[111].revelation == "meccan"


def test_a_surah_that_does_not_match_the_numbering_is_refused():
    with pytest.raises(InvalidSurahData, match="the numbering says 4"):
        Surah(112, "الإخلاص", "Al-Ikhlaas", "Sincerity", "meccan", 5)
    with pytest.raises(InvalidSurahData, match="revelation"):
        Surah(112, "الإخلاص", "Al-Ikhlaas", "Sincerity", "makki", 4)


def test_a_name_slug_is_plain_ascii():
    assert name_slug("Ash-Shu'araa") == "ash-shuara" and name_slug("Al-Muminoon") == "al-muminun"


# ---------------------------------------------------------------- the pages

def _view(**changes) -> dict:
    view = {"number": 112, "slug": "112-al-ikhlas", "arabic": "الإخلاص", "transliteration": "Al-Ikhlaas",
            "english": "Sincerity", "revelation": "meccan", "ayahCount": 4, "tokens": 15, "covered": 11, "coverage": 73,
            "entryCount": 10,
            "taught": [{"order": 0, "family": "verb", "slug": "qala", "arabic": "قالَ", "meaning": {"bs": "reći", "en": "to say"},
                        "root": "قول", "count": 1, "forms": [{"arabic": "قُلْ", "count": 1, "gloss": {"bs": "reci", "en": "say"}}],
                        "first": "112:1", "ayahAudio": "https://cdn.islamic.network/quran/audio/64/ar.alafasy/6222.mp3",
                        "audio": "audio/abc.m4a"},
                       {"order": 3, "family": "noun", "slug": "ahad", "arabic": "أَحَد", "meaning": {"bs": "jedan", "en": "one"},
                        "root": "أحد", "count": 2, "forms": [{"arabic": f"أَحَدٌ{index}", "count": 1} for index in range(8)],
                        "first": "112:1", "ayahAudio": "https://cdn.islamic.network/quran/audio/64/ar.alafasy/6222.mp3",
                        "audio": None}],
            "untaught": [{"arabic": "صَمَد", "count": 1, "order": 4}],
            "practice": ["verb:qala"], "ayatFile": "ayat/sura-112.json", "ayatTranslations": {"en": "ayat/sura-112.en.json"}}
    return {**view, **changes}


@pytest.fixture(scope="module")
def texts():
    return load_texts()


def _language(code: str):
    return next(language for language in LANGUAGES if language.code == code)


def test_a_surah_page_shows_coverage_rows_and_the_untaught_words_closed(texts):
    html = surah_render.surah_page(_view(), _language("bs"), texts["bs"], published={render.NOUNS, render.SURAHS})
    assert "Ovdje učiš 73% riječi ove sure: 11 od 15." in html
    assert '<a href="../../../bs/qala/" lang="ar" dir="rtl" translate="no" class="notranslate">قالَ</a>' in html
    assert '../../../bs/imenica/ahad/' in html
    assert 'قُلْ</b> 1× reci <span class="ai">AI</span>' in html
    assert "<small>+5</small>" in html                         # eight forms: three shown, five counted
    assert '<details class="untaught">' in html and "jedan" in html
    assert "صَمَد <small>1×</small>" in html and html.count("صَمَد") == 1   # its count, no meaning
    assert 'data-audio="../../../audio/abc.m4a"' in html
    assert 'data-ayat="../../../ayat/sura-112.json"' in html and 'data-translation-language="en"' in html
    assert "korijen" not in html                              # no root page is published yet


def test_a_card_whose_section_is_not_published_is_not_linked(texts):
    html = surah_render.surah_page(_view(), _language("en"), texts["en"], published={render.SURAHS})
    assert "en/noun/ahad/" not in html and "en/qala/" in html


def test_a_root_is_linked_only_where_its_page_exists(texts):
    pages = {("bs", "قول"): "bs/korijen/qwl/"}
    html = surah_render.surah_page(_view(), _language("bs"), texts["bs"], published=set(),
                                   root_path=lambda language, root: pages.get((language, root)))
    assert html.count("bs/korijen/") == 1 and 'href="../../../bs/korijen/qwl/"' in html


def test_every_arabic_word_on_a_surah_page_is_kept_from_browser_translation(texts):
    html = surah_render.surah_page(_view(), _language("en"), texts["en"], published={render.SURAHS})
    arabic = re.findall(r'<[^>]+lang="ar"[^>]*>', html)
    assert arabic and all('translate="no"' in tag for tag in arabic)


def test_the_surah_list_links_every_surah(texts):
    html = surah_render.surah_index([_view(), _view(number=1, slug="1-al-fatiha")], _language("en"), texts["en"],
                                    published={render.SURAHS})
    assert 'href="112-al-ikhlas/"' in html and 'href="1-al-fatiha/"' in html and "73% known" in html


def test_the_practice_link_asks_about_the_surahs_words_that_have_questions(texts):
    kinds = {"verb:qala": ("quran-form", "listen"), "noun:ahad": ("picture",), **{f"noun:n{i}": ("listen",) for i in range(40)}}
    link = words_practice_link(["verb:qala", "pronoun:huwa", "noun:ahad"], kinds, _language("bs"), texts["bs"],
                               "../../../", for_surah=True)
    assert "?w=verb:qala,noun:ahad&amp;t=picture,listen,quran-form&amp;s=surah" in link
    assert "Vježbaj riječi ove sure →" in link
    many = words_practice_link([f"noun:n{i}" for i in range(40)], kinds, _language("en"), texts["en"], "", for_surah=True)
    assert many.count("noun:n") == MAX_SURAH_WORDS
    assert words_practice_link(["pronoun:huwa"], kinds, _language("bs"), texts["bs"], "", for_surah=True) == ""


# ---------------------------------------------------------------- the built site

built = pytest.mark.skipif(not (PAGES_DIR / "bs" / "sura" / "index.html").is_file(),
                           reason="build/pages has no surah pages (run `fil pages`)")


class _Counts(HTMLParser):
    """The counts a surah page's rows show, taught and untaught."""

    def __init__(self) -> None:
        super().__init__()
        self.counts: list[int] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        found = dict(attrs)
        if tag == "li" and "data-count" in found:
            self.counts.append(int(found["data-count"]))


@built
def test_every_built_surah_page_accounts_for_every_word_of_its_surah():
    for language in ("bs", "en"):
        folder = PAGES_DIR / language / seo.SURAH_FOLDERS[language]
        pages = sorted(folder.glob("*/index.html"))
        assert len(pages) == 114
        for page in pages:
            html = page.read_text(encoding="utf-8")
            parser = _Counts()
            parser.feed(html)
            tokens = int(re.search(r'data-tokens="(\d+)"', html).group(1))
            assert sum(parser.counts) == tokens, page


@built
def test_al_ikhlas_built_page_has_its_fifteen_words_and_a_sane_weight():
    page = PAGES_DIR / "bs" / "sura" / "112-al-ikhlas" / "index.html"
    html = page.read_text(encoding="utf-8")
    assert 'data-tokens="15"' in html and "قالَ" in html
    # al-Baqarah, the longest list: 700-odd taught rows, the rest folded; what travels is the compressed page.
    baqara = (PAGES_DIR / "en" / "surah" / "2-al-baqara" / "index.html").read_bytes()
    assert len(baqara) < 800_000 and len(gzip.compress(baqara)) < 100_000
    assert '<details class="more-words">' in baqara.decode("utf-8")
