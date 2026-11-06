"""The noun engine: reading nouns from the corpus, the catalogue, the gate, the case table.

The golden tests at the end encode hand-verified case tables of five nouns
(كِتَاب، أَرْض، شَجَرَة، يَد، مُؤْمِن) and check what the engine builds from the real
corpus — and, where CAMeL Tools is installed, what it generates — against them.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from fil.composition.decomposition import AND
from fil.corpus.nouns import BI, iter_noun_occurrences
from fil.corpus.parse import iter_segments
from fil.nouns import gate
from fil.nouns.catalogue import build_catalogue, plural_kind, plural_pattern
from fil.nouns.model import (ACCUSATIVE, ACTIVE_PARTICIPLE, ATTESTED, BROKEN, CASES, CONSTRUCT, DEFINITE, DUAL,
                             GENERATED, GENITIVE, INDEFINITE, MISSING, NOMINATIVE, PLURAL, SINGULAR, SOUND_FEMININE,
                             SOUND_MASCULINE, STATES, Cell, NounLemma, NounOccurrence, PluralForm)
from fil.nouns.paradigm import build_paradigm, generated_cell, has_quranic_vowels
from fil.nouns.spelling import skeleton, spelling_key, standalone
from fil.resources import QAC_MORPHOLOGY


def occurrences(*words: Sequence[str]) -> list[NounOccurrence]:
    """Noun occurrences from consecutive QAC words, each a list of "surface POS features"."""
    lines = [f"2:1:{number}:{index}\t" + "\t".join(segment.split(" ", 2))
             for number, word in enumerate(words, 1) for index, segment in enumerate(word, 1)]
    return list(iter_noun_occurrences(iter_segments(iter(lines))))


BI_AYDIHIM = ["بِ P P|PREF|LEM:ب", "أَيْدِي N ROOT:يدي|LEM:يَد|FP|GEN", "هِمْ N PRON|SUFF|3MP"]
WA_L_ARDI = ["وَ P CONJ|PREF|LEM:و", "ٱلْ P DET|PREF|LEM:ال", "أَرْضِ N ROOT:أرض|LEM:أَرْض|F|GEN"]
FI = ["فِى P P|LEM:فِي"]
AL_ARDI = ["ٱلْ P DET|PREF|LEM:ال", "أَرْضِ N ROOT:أرض|LEM:أَرْض|F|GEN"]
YAWMA_IDHIN = ["يَوْمَ N T|ROOT:يوم|LEM:يَوْم|M|ACC", "ئِذٍ N T|LEM:إِذ"]
KITABUN = ["كِتَٰبٌ N ROOT:كتب|LEM:كِتاب|M|INDEF|NOM"]


# ---------------------------------------------------------------- reading the corpus

def test_takes_a_word_apart_preposition_broken_plural_possessor():
    (noun,) = occurrences(BI_AYDIHIM)
    assert (noun.word_text, noun.stem, noun.lemma) == ("بِأَيْدِيهِمْ", "أَيْدِي", "يَد")
    assert (noun.gender, noun.number, noun.case, noun.state) == ("F", PLURAL, GENITIVE, CONSTRUCT)
    assert noun.parts.proclitics == (BI,)
    assert noun.parts.possessive == "3MP"
    assert noun.parts.governing_preposition == "ب"


def test_a_conjunction_and_the_article():
    (noun,) = occurrences(WA_L_ARDI)
    assert noun.parts.proclitics == (AND,) and noun.parts.has_article
    assert noun.state == DEFINITE
    assert noun.parts.governing_preposition is None


def test_the_preposition_of_the_word_before_governs_the_genitive():
    (noun,) = occurrences(FI, AL_ARDI)
    assert noun.parts.governing_preposition == "فِي"
    assert noun.is_bare


def test_a_bare_masculine_tag_is_singular_and_nunation_is_indefinite():
    (noun,) = occurrences(KITABUN)
    assert (noun.gender, noun.number, noun.state) == ("M", SINGULAR, INDEFINITE)


UKHRA_NOM = ["أُخْرَىٰ N ROOT:أخر|LEM:آخَر|FS|NOM"]
UKHARA_GEN = ["أُخَرَ N ROOT:أخر|LEM:آخَر|FP|GEN|ADJ"]
AWLIYAA_ACC = ["أَوْلِيَآءَ N ROOT:ولي|LEM:وَلِيّ|MP|ACC"]
AAMA_NOM = ["أَعْمَىٰ N ROOT:عمي|LEM:أَعْمَى|M|NOM"]
HUDA_CONSTRUCT = ["هُدَى N ROOT:هدي|LEM:هُدَى|M|NOM"]
ALLAHI = ["ٱللَّهِ N PN|ROOT:أله|LEM:اللَّه|GEN"]
MIN = ["مِنْ P P|LEM:مِن"]
QALAT = ["قَالَتْ V PERF|VF:1|ROOT:قول|LEM:قالَ|3FS"]
LA = ["لَا P NEG|LEM:لا"]
MAWLA = ["مَوْلَىٰ N ROOT:ولي|LEM:مَوْلَى|M|ACC"]
YA_SAMAU = ["يَٰ P VOC|PREF|LEM:ي", "سَمَآءُ N ROOT:سمو|LEM:سَماء|F|NOM"]


@pytest.mark.parametrize("words", [
    (UKHRA_NOM, QALAT),          # alif maqṣūra: no nunation to show (2:282 … أُخْرَىٰ)
    (AAMA_NOM,),                 # at the ayah's end nothing can possess it
    (AWLIYAA_ACC, MIN),          # a diptote in -āʾ before a preposition (أَوْلِيَآءَ مِن دُونِ)
    (UKHARA_GEN, QALAT),         # a genitive in fatḥa is a diptote's, never a construct's
])
def test_a_noun_that_cannot_take_nunation_is_indefinite_without_a_possessor(words):
    assert occurrences(*words)[0].state == INDEFINITE


@pytest.mark.parametrize("words", [
    (HUDA_CONSTRUCT, ALLAHI),    # هُدَى ٱللَّهِ: before its possessor it is in construct
    (LA, MAWLA, MIN),            # لَا مَوْلَىٰ: the bare form is not the indefinite cell (مَوْلًى)
    (YA_SAMAU, QALAT),           # the called يَٰسَمَآءُ
])
def test_the_same_shape_stays_in_construct_when_it_is_not_an_indefinite_cell(words):
    noun = next(occurrence for occurrence in occurrences(*words) if occurrence.lemma != "اللَّه")
    assert noun.state == CONSTRUCT


def test_a_word_beyond_the_rules_is_kept_with_its_reason():
    (noun,) = occurrences(YAWMA_IDHIN)
    assert not noun.is_clean
    assert noun.skip_reason == "unknown suffix"


def test_rootless_nouns_are_not_read():
    assert occurrences(["هُوَ N PRON|3MS"]) == []


# ---------------------------------------------------------------- the catalogue

@pytest.mark.parametrize("lemma, plural, kind", [
    ("يَد", "أَيْدِي", BROKEN),
    ("رَسُول", "رُسُلُ", BROKEN),
    ("مُؤْمِن", "مُّؤْمِنُونَ", SOUND_MASCULINE),
    ("مُتَّقي", "مُتَّقِينَ", SOUND_MASCULINE),          # a defective singular loses its yāʾ
    ("نَبِيّ", "ٱلنَّبِيِّۦنَ", SOUND_MASCULINE),          # the small yāʾ is a letter
    ("ثَمَرَة", "ثَّمَرَٰتِ", SOUND_FEMININE),
    ("سَماء", "سَمَٰوَٰتِ", SOUND_FEMININE),
    ("صَلاة", "صَلَوَٰتِ", SOUND_FEMININE),
    ("مَيِّت", "أَمْوَٰتًا", BROKEN),                     # ends in -āt, yet broken
    ("سِنِين", "السِّنُونَ", SOUND_MASCULINE),             # a plural-only lemma with its own ending
    ("سِنِين", "سِنِينَ", SOUND_MASCULINE),
    ("طِين", "طِينٌ", BROKEN),                           # a singular in -īn is no sound plural
])
def test_tells_sound_plurals_from_broken_ones(lemma, plural, kind):
    assert plural_kind(lemma, plural) == kind


def test_catalogue_aggregates_ranks_and_links_to_our_verbs():
    found = occurrences(KITABUN, KITABUN, BI_AYDIHIM,
                        ["مُؤْمِنُ N ACT_PCPL|VF:4|ROOT:أمن|LEM:مُؤْمِن|MP|NOM", "ونَ N PRON|SUFF|3MP"])
    lemmas = {lemma.lemma: lemma for lemma in build_catalogue(found, ["كتب_1", "أمن_1", "أمن_4"])}
    assert lemmas["كِتاب"].rank == 1 and lemmas["كِتاب"].count == 2
    assert lemmas["كِتاب"].linked_verb == "كتب_1"
    assert lemmas["مُؤْمِن"].kind == ACTIVE_PARTICIPLE
    assert lemmas["مُؤْمِن"].linked_verb == "أمن_4"   # a participle links to its own form
    assert lemmas["يَد"].linked_verb is None
    assert [(plural.text, plural.kind) for plural in lemmas["يَد"].plurals] == [("أَيْدِي", BROKEN)]
    assert lemmas["يَد"].numbers == (SINGULAR, PLURAL)   # the singular, though only the plural is seen


def test_a_plural_lemmatised_as_itself_has_no_singular_row():
    (nas,) = build_catalogue(occurrences(["نَّاسِ N ROOT:نوس|LEM:ناس|MP|GEN"]))
    assert nas.numbers == (PLURAL,)


# ---------------------------------------------------------------- spelling

def test_one_spelling_key_for_uthmani_imlai_and_camel():
    assert spelling_key("ٱلْكِتَٰبُ") == spelling_key("الْكِتَابُ") == spelling_key("الكِتابُ")
    assert spelling_key("كِتَٰبًا") == spelling_key("كِتاباً")
    assert spelling_key("ذُرِّيَّٰتٍ") == spelling_key("ذُرِّيّاتٍ")
    assert spelling_key("نَهَرٌ") != spelling_key("نَهْرٌ")


def test_uthmani_silent_waw_and_dropped_article_lam_fold_to_imlai():
    assert spelling_key("ٱلصَّلَوٰةُ") == spelling_key("الصَّلَاةُ")
    assert spelling_key("حَيَوٰةٌ") == spelling_key("حَيَاةٌ")
    assert spelling_key("ٱلَّيْلُ") == spelling_key("اللَّيْلُ")
    assert spelling_key("ٱلسَّمَٰوَٰتِ") == spelling_key("السَّمَاوَاتِ")   # a voweled wāw stays a wāw
    assert spelling_key("ٱلرِّبَوٰا۟") == spelling_key("الرِّبَا")   # the silent alif after the seat
    assert spelling_key("كَفَرُوا۟") == spelling_key("كَفَرُوا")   # a silent alif after a voweled wāw stays


def test_skeleton_and_standalone():
    assert skeleton("ءَايَٰتِ") == skeleton("ـَٔايَٰتِ") == skeleton("آيات")
    assert skeleton("أَيَّىٰمٍ") == "ءيام"
    assert standalone("سَّمَٰوَٰتِ") == "سَمَٰوَٰتِ"
    assert standalone("ـَٔايَٰتِ") == "ءَايَٰتِ"


# ---------------------------------------------------------------- the gate

@pytest.mark.parametrize("form, cell", [
    ("كِتَابًا", Cell(SINGULAR, INDEFINITE, ACCUSATIVE)),
    ("حَقًّا", Cell(SINGULAR, INDEFINITE, ACCUSATIVE)),
    ("ٱلدُّنْيَا", Cell(SINGULAR, DEFINITE, GENITIVE)),
    ("الْأَيْدِي", Cell(PLURAL, DEFINITE, NOMINATIVE)),
    ("أَيْدٍ", Cell(PLURAL, INDEFINITE, GENITIVE)),
    ("أَشْيَآءَ", Cell(PLURAL, INDEFINITE, GENITIVE)),   # a diptote
    ("ٱلثَّمَرَٰتِ", Cell(PLURAL, DEFINITE, ACCUSATIVE)),
    ("مُؤْمِنِينَ", Cell(PLURAL, INDEFINITE, GENITIVE)),
    ("يَدَانِ", Cell(DUAL, INDEFINITE, NOMINATIVE)),
])
def test_the_gate_passes_well_formed_cells(form, cell):
    lemmas = {"أَشْيَآءَ": "شَىْء", "ٱلثَّمَرَٰتِ": "ثَمَرَة", "مُؤْمِنِينَ": "مُؤْمِن", "يَدَانِ": "يَد"}
    assert gate.problems(form, cell, lemmas.get(form, "يَد")) == ()


@pytest.mark.parametrize("form, cell, problem", [
    ("الأَيْدِيُ", Cell(PLURAL, DEFINITE, NOMINATIVE), "case vowel on a defective yāʾ"),
    ("السَعْيُ", Cell(SINGULAR, DEFINITE, NOMINATIVE), "sun letter after the article not doubled"),
    ("كِتَابٌ", Cell(SINGULAR, DEFINITE, NOMINATIVE), "definite without the article"),
    ("أَلِيمٌ", Cell(SINGULAR, INDEFINITE, NOMINATIVE), None),   # a hamza, not the article
    ("ٱلْأَيْدِى", Cell(PLURAL, DEFINITE, ACCUSATIVE), "ACC ending expected, found no vowel"),
    ("ٱلْجَنَّتَيْنِ", Cell(DUAL, DEFINITE, NOMINATIVE), "NOM D must end in -انِ"),
    ("حَيََّاتٌ", Cell(PLURAL, INDEFINITE, NOMINATIVE), "two vowels on one letter"),
])
def test_the_gate_refuses_what_says_another_cell(form, cell, problem):
    found = gate.problems(form, cell, "أَلِيم" if problem is None else "يَد")
    assert found == () if problem is None else problem in found


# ---------------------------------------------------------------- generated cells

YAD = NounLemma("يَد", "يدي", "noun", "F", 120, 37, None, (PluralForm("أَيْدِي", BROKEN, 66),), 33, (), None,
                (SINGULAR, PLURAL))
AYDI = frozenset({plural_pattern(BROKEN, "أَيْدِي")})


def test_a_generated_plural_must_be_the_qurans_pattern():
    cell = Cell(PLURAL, INDEFINITE, GENITIVE)
    chosen = generated_cell(YAD, cell, ("أَيادٍ", "أَيْدٍ"), AYDI)
    assert (chosen.text, chosen.source) == ("أَيْدٍ", GENERATED)
    refused = generated_cell(YAD, cell, ("أَيادٍ",), AYDI)
    assert refused.source == MISSING and refused.problems == ("not the Quran's pattern",)


def test_two_quranic_candidates_are_a_choice_not_a_cell():
    chosen = generated_cell(YAD, Cell(SINGULAR, DEFINITE, NOMINATIVE), ("الْيَدُ", "الْيَدُّ"), frozenset())
    assert chosen.source == MISSING and chosen.problems[0].startswith("ambiguous")


def test_the_stem_must_be_voweled_like_the_quran():
    assert not has_quranic_vowels("نَهْرٌ", "نَهَر")
    assert has_quranic_vowels("الْأَنْهارِ", "أَنْهَٰرُ")
    assert has_quranic_vowels("قادِرِينَ", "قَٰدِرُونَ", ending_length=2)


class _Fake:
    def __init__(self, forms: dict[str, tuple[str, ...]]) -> None:
        self.forms = forms

    def generate(self, lemma: NounLemma, cell: Cell) -> tuple[str, ...]:
        return self.forms.get(cell.code, ())


def test_the_quran_fills_a_cell_first_and_the_generator_the_rest():
    found = occurrences(KITABUN)
    (lemma,) = build_catalogue(found)
    paradigm = build_paradigm(lemma, found, _Fake({"S|definite|NOM": ("الْكِتابُ",)}))
    assert paradigm.text(SINGULAR, INDEFINITE, NOMINATIVE) == "كِتَٰبٌ"
    assert paradigm.text(SINGULAR, DEFINITE, NOMINATIVE) == "الْكِتابُ"
    assert (paradigm.count(ATTESTED), paradigm.count(GENERATED), paradigm.count(MISSING)) == (1, 1, 4)


# ---------------------------------------------------------------- golden: five nouns, hand-verified

def _row(definite: str, indefinite: str) -> dict[tuple[str, str], str | None]:
    """Three definite then three indefinite forms, NOM ACC GEN; "-" is a cell left empty."""
    forms = definite.split() + indefinite.split()
    return {(state, case): (None if form == "-" else form)
            for (state, case), form in zip([(s, c) for s in STATES for c in CASES], forms)}


GOLDEN = {
    "كِتاب": {SINGULAR: _row("الْكِتَابُ الْكِتَابَ الْكِتَابِ", "كِتَابٌ كِتَابًا كِتَابٍ"),
              PLURAL: _row("الْكُتُبُ الْكُتُبَ الْكُتُبِ", "كُتُبٌ كُتُبًا كُتُبٍ")},
    "أَرْض": {SINGULAR: _row("الْأَرْضُ الْأَرْضَ الْأَرْضِ", "أَرْضٌ أَرْضًا أَرْضٍ")},
    "شَجَرَة": {SINGULAR: _row("الشَّجَرَةُ الشَّجَرَةَ الشَّجَرَةِ", "شَجَرَةٌ شَجَرَةً شَجَرَةٍ")},
    "يَد": {SINGULAR: _row("الْيَدُ الْيَدَ الْيَدِ", "يَدٌ يَدًا يَدٍ"),
            DUAL: _row("الْيَدَانِ الْيَدَيْنِ الْيَدَيْنِ", "يَدَانِ يَدَيْنِ يَدَيْنِ"),
            # أَيْدِيًا: CAMeL has no indefinite accusative — the cell stays empty, never wrong
            PLURAL: _row("الْأَيْدِي الْأَيْدِيَ الْأَيْدِي", "أَيْدٍ - أَيْدٍ")},
    "مُؤْمِن": {SINGULAR: _row("الْمُؤْمِنُ الْمُؤْمِنَ الْمُؤْمِنِ", "مُؤْمِنٌ مُؤْمِنًا مُؤْمِنٍ"),
                DUAL: _row("الْمُؤْمِنَانِ الْمُؤْمِنَيْنِ الْمُؤْمِنَيْنِ", "مُؤْمِنَانِ مُؤْمِنَيْنِ مُؤْمِنَيْنِ"),
                PLURAL: _row("الْمُؤْمِنُونَ الْمُؤْمِنِينَ الْمُؤْمِنِينَ", "مُؤْمِنُونَ مُؤْمِنِينَ مُؤْمِنِينَ")},
}

needs_corpus = pytest.mark.skipif(not QAC_MORPHOLOGY.exists(), reason="the corpus is not downloaded")


@pytest.fixture(scope="module")
def quran() -> tuple[list[NounOccurrence], dict[str, NounLemma]]:
    with QAC_MORPHOLOGY.open(encoding="utf-8") as lines:
        found = list(iter_noun_occurrences(iter_segments(lines)))
    lemmas = {lemma.lemma: lemma for lemma in build_catalogue(found) if lemma.lemma in GOLDEN}
    return [occurrence for occurrence in found if occurrence.lemma in GOLDEN], lemmas


def _paradigm(quran, lemma: str, generator=None):
    found, lemmas = quran
    entry = lemmas[lemma]
    return entry, build_paradigm(entry, [o for o in found if (o.lemma, o.root) == (entry.lemma, entry.root)], generator)


@needs_corpus
@pytest.mark.parametrize("lemma", list(GOLDEN))
def test_golden_numbers_and_quranic_spellings(quran, lemma):
    """Without a generator: the rows are the golden ones, and every cell the Quran fills is right."""
    entry, paradigm = _paradigm(quran, lemma)
    assert entry.numbers == tuple(GOLDEN[lemma])
    for found in paradigm.cells:
        if found.source == ATTESTED:
            assert spelling_key(found.text) == spelling_key(GOLDEN[lemma][found.cell.number][(found.cell.state,
                                                                                                found.cell.case)])


@needs_corpus
@pytest.mark.parametrize("lemma", list(GOLDEN))
def test_golden_full_tables_with_camel(quran, lemma):
    pytest.importorskip("camel_tools")
    from fil.camel_nouns import CamelNounGenerator

    try:
        _entry, paradigm = _paradigm(quran, lemma, CamelNounGenerator())
    except Exception as missing:  # noqa: BLE001 - the morphology DB is a separate download
        pytest.skip(f"CAMeL database unavailable: {missing}")
    for found in paradigm.cells:
        expected = GOLDEN[lemma][found.cell.number][(found.cell.state, found.cell.case)]
        actual = found.text and spelling_key(found.text)
        assert actual == (expected and spelling_key(expected)), found.cell.code
