"""Vježbe / Exercises: every generator gives exactly one right answer and only fair distractors,
the gate refuses what a learner could fairly call right twice, and the pages carry what the script needs."""

from __future__ import annotations

import json
import re

import pytest

from fil.adjectives.agreement import AdjectiveReading, NounReading
from fil.exercises import gate
from fil.exercises.agreement import AdjectiveForm, AdjectiveSentence, agreement_exercises, is_allowed
from fil.exercises.ayat import (AyahWord, CitedAyah, NuanceGroup, NuanceMember, ParticleUse, nuance_exercises,
                                particle_exercises)
from fil.exercises.cases import NounSentence, SentenceWord, case_exercises
from fil.exercises.model import (CASE, KINDS, LISTEN, PICTURE, Bilingual, Exercise, InvalidExercise, Option, Segment,
                                 word_id)
from fil.exercises.prepositions import NounForms, QuranicForm, TableRow, preposition_exercises
from fil.exercises.shards import shard_of, shards
from fil.exercises.text import in_one_style, meanings_overlap, same_spelling
from fil.exercises.vocabulary import (Word, could_be_pictured_alike, is_fair_distractor, listen_exercises,
                                     picture_exercises)
from fil.languages import LANGUAGES
from fil.nouns.model import ACCUSATIVE, DEFINITE, FEMININE, GENITIVE, INDEFINITE, MASCULINE, NOMINATIVE, PLURAL, SINGULAR, Cell
from fil.nouns.spelling import spelling_key
from fil.nouns.pictures import OPENMOJI, OWN_DRAWING, TWEMOJI, NounPicture
from fil.pages import exercise_render
from fil.stages import exercise_pages
from fil.stages.exercises import ExerciseSets

B = Bilingual
BS_EN = {language.code: language for language in LANGUAGES}


def _right(exercise: Exercise) -> Option:
    (right,) = exercise.correct
    return right


# ---------------------------------------------------------------- the gate

def _exercise(*options: Option, kind: str = LISTEN, key: str = "x") -> Exercise:
    return Exercise(kind=kind, key=key, words=("noun:x",), options=options)


def test_the_gate_wants_exactly_one_right_option():
    assert gate.problems(_exercise(Option(True, code="a"), Option(False, code="b"))) == []
    assert "0 right options" in " ".join(gate.problems(_exercise(Option(False, code="a"), Option(False, code="b"))))
    assert "2 right options" in " ".join(gate.problems(_exercise(Option(True, code="a"), Option(True, code="b"))))


def test_the_gate_refuses_two_options_that_are_one_word_or_one_meaning():
    same_word = _exercise(Option(True, arabic="ٱلْأَرْضِ"), Option(False, arabic="الْأَرْضِ"))
    assert any("one word" in problem for problem in gate.problems(same_word))
    same_meaning = _exercise(Option(True, meaning=B("srce", "heart")), Option(False, meaning=B("srce, duša", "soul")))
    assert any("overlap" in problem for problem in gate.problems(same_meaning))


def test_the_gate_refuses_mixed_options_missing_languages_and_repeated_keys():
    mixed = _exercise(Option(True, code="a"), Option(False, arabic="بَيْت"))
    assert any("several sorts" in problem for problem in gate.problems(mixed))
    untranslated = _exercise(Option(True, meaning=B("kuća", "")), Option(False, meaning=B("put", "way")))
    assert any("missing a language" in problem for problem in gate.problems(untranslated))
    twice = _exercise(Option(True, code="a"), Option(False, code="b"))
    with pytest.raises(InvalidExercise, match="key used 2 times"):
        gate.check([twice, twice])


def test_a_blanked_passage_must_have_its_blank():
    exercise = Exercise(kind="nuance", key="x", words=("nuance:x",), passage=(Segment("قَالَ"),),
                        options=(Option(True, arabic="قَالَ"), Option(False, arabic="كَلَّمَ")))
    assert "the passage has no blank" in gate.problems(exercise)


# ---------------------------------------------------------------- spelling and meaning

def test_options_are_shown_in_one_style_without_changing_the_word():
    assert in_one_style("ٱلْأَرْضِ") == "الْأَرْضِ"           # Uthmani wasla → standard alif
    assert in_one_style("الرَّحِيمانِ") == "الرَّحِيمَانِ"     # CAMeL's bare letter before ā gets its fatḥa
    assert in_one_style("قَالُوا") == "قَالُوا"               # the silent alif after a plural wāw is left alone
    assert in_one_style("ٱلْإِنسَٰنُ") == "الْإِنسَانُ"
    for form in ("ٱلْأَرْضِ", "الرَّحِيمانِ", "ٱلْإِنسَٰنُ", "مُبِينًا"):
        assert same_spelling(in_one_style(form), form)


def test_meanings_overlap_on_a_shared_content_word_in_either_language():
    assert meanings_overlap(B("srce", "heart"), B("srce, duša", "soul"))
    assert meanings_overlap(B("narod", "people, nation"), B("ljudi", "people"))
    assert not meanings_overlap(B("reći", "to say"), B("doći", "to come"))   # "to" carries no meaning


# ---------------------------------------------------------------- picture → word, listen → meaning

def _word(slug: str, arabic: str, root: str, bs: str, en: str, rank: int, *, emoji: str | None = None,
          category: str = "body", family: str = "noun") -> Word:
    return Word(id=word_id(family, slug), arabic=arabic, root=root, meaning=B(bs, en), rank=rank, sound=f"audio/{slug}.m4a",
                picture=f"pictures/{slug}.svg" if family == "noun" else None, emoji=emoji or slug, category=category)


HEART = _word("qalb", "قَلْب", "قلب", "srce", "heart", 1, category="body_parts")
FUAD = _word("fuad", "فُؤَاد", "فأد", "srce", "heart", 2, category="body_parts")
SADR = _word("sadr", "صَدْر", "صدر", "prsa, grudi", "breast", 3, category="body_parts")
TREE = _word("shajara", "شَجَرَة", "شجر", "drvo", "tree", 4, category="fruit_vegetables")
TREES = _word("shajar", "شَجَر", "شجر", "drveće", "trees", 5, category="fruit_vegetables")
HAND = _word("yad", "يَد", "يدي", "ruka", "hand", 6, category="body_parts")
DOOR = _word("bab", "بَاب", "بوب", "vrata", "door", 7, category="house_objects")
DOG = _word("kalb", "كَلْب", "كلب", "pas", "dog", 8, category="animals")
SHIRT = _word("qamis", "قَمِيص", "قمص", "košulja", "shirt", 9, category="clothing")
GRAPES = _word("inab", "عِنَب", "عنب", "grožđe", "grapes", 10, category="fruit_vegetables")
FOOD = _word("taam", "طَعَام", "طعم", "hrana", "food", 11, category="food_drink")
SEA = _word("bahr", "بَحْر", "بحر", "more", "sea", 12, emoji="1F30A", category="water_sea")
YAMM = _word("yamm", "يَمّ", "يمم", "more (rijeka)", "the sea", 13, emoji="1F30A", category="water_sea")
RAIN = _word("matar", "مَطَر", "مطر", "kiša", "rain", 14, category="nature_sky")
WORDS = [HEART, FUAD, SADR, TREE, TREES, HAND, DOOR, DOG, SHIRT, GRAPES, FOOD, SEA, YAMM, RAIN]
SYNONYMS = [frozenset({"noun:qalb", "noun:fuad", "noun:sadr"})]


def test_a_distractor_is_never_a_synonym_a_sibling_of_its_root_or_drawn_alike():
    assert not is_fair_distractor(HEART, FUAD)                       # one meaning
    assert not is_fair_distractor(HEART, SADR, SYNONYMS)             # one nuance group
    assert not is_fair_distractor(TREE, TREES)                       # one root
    assert not is_fair_distractor(SEA, YAMM)                         # one picture (and one meaning)
    assert is_fair_distractor(HEART, HAND, SYNONYMS)


def test_picture_exercises_have_one_right_word_and_distractors_no_picture_could_pass_for():
    built = {exercise.key: exercise for exercise in picture_exercises(WORDS, SYNONYMS)}
    heart = built["qalb"]
    assert _right(heart).arabic == "قَلْب" and heart.picture == "pictures/qalb.svg"
    assert len(heart.options) == 4
    by_arabic = {word.arabic: word for word in WORDS}
    for exercise in built.values():
        answer = by_arabic[_right(exercise).arabic]
        for option in exercise.options[1:]:
            other = by_arabic[option.arabic]
            assert other.category != answer.category          # no hand beside a heart, no tree beside grapes
            assert not could_be_pictured_alike(answer, other)  # no "food" beside grapes, no rain beside the sea
        assert gate.problems(exercise) == []
    grapes = {option.arabic for option in built["inab"].options}
    assert not grapes & {"طَعَام", "شَجَرَة", "شَجَر"}


def test_listen_exercises_ask_a_meaning_among_meanings_of_the_same_family():
    verbs = [_word(f"v{rank}", arabic, root, bs, en, rank, family="verb") for rank, (arabic, root, bs, en) in enumerate(
        [("قَالَ", "قول", "reći", "to say"), ("كَانَ", "كون", "biti", "to be"), ("جَاءَ", "جيأ", "doći", "to come"),
         ("أَتَى", "أتي", "doći, donijeti", "to come, to bring"), ("عَلِمَ", "علم", "znati", "to know")], start=1)]
    built = {exercise.key: exercise for exercise in listen_exercises([*WORDS, *verbs])}
    came = built["verb-v3"]
    assert came.sound == "audio/v3.m4a" and _right(came).meaning == B("doći", "to come")
    assert B("doći, donijeti", "to come, to bring") not in {option.meaning for option in came.options}
    assert all(not option.meaning.en.startswith(("heart", "sea")) for option in came.options)   # verbs only
    assert all(gate.problems(exercise) == [] for exercise in built.values())


# ---------------------------------------------------------------- which case?

def _sentence(role: str, *words: tuple[str, bool]) -> NounSentence:
    return NounSentence(word="noun:bayt", role=role, translation=B("rečenica", "sentence"),
                        words=tuple(SentenceWord(arabic, is_target, B("kuća", "house")) for arabic, is_target in words))


def test_the_case_of_a_marked_noun_is_its_checked_role():
    built = case_exercises([
        _sentence("subject", ("الْبَيْتُ", True), ("كَبِيرٌ", False)),
        _sentence("preposition", ("جَلَسَ", False), ("فِي", False), ("الْبَيْتِ", True)),
        _sentence("possession", ("بَابُ", False), ("الْبَيْتِ", True)),
        _sentence("object", ("بَنَى", False), ("بَيْتًا", True), ("بَيْتًا", True)),   # two marks: not askable
    ])
    assert [(_right(exercise).code, exercise.facts["case"]) for exercise in built] == [
        ("subject", NOMINATIVE), ("preposition", GENITIVE), ("possession", GENITIVE)]
    assert all(len(exercise.options) == 4 and gate.problems(exercise) == [] for exercise in built)
    assert [segment.is_marked for segment in built[1].passage] == [False, False, True]


# ---------------------------------------------------------------- preposition + case

def _table(number: str, state: str, nominative: str, accusative: str, genitive: str) -> TableRow:
    return TableRow(number, {(state, NOMINATIVE): nominative, (state, ACCUSATIVE): accusative, (state, GENITIVE): genitive})


def _form(arabic: str, *, number: str = SINGULAR, state: str = DEFINITE, count: int = 10, preposition: str = "فِي") -> QuranicForm:
    return QuranicForm(preposition=preposition, arabic=arabic, number=number, state=state, case=GENITIVE, reference="2:11",
                       count=count, sound="audio/fi-ard.m4a", gloss=B("na zemlji", "in the earth"), bosnian_case="L")


def test_after_a_preposition_the_right_ending_is_the_genitive_the_quran_says():
    earth = NounForms("noun:ard", (_table(SINGULAR, DEFINITE, "ٱلْأَرْضُ", "ٱلْأَرْضَ", "ٱلْأَرْضِ"),), (_form("ٱلْأَرْضِ"),))
    (exercise,) = preposition_exercises([earth])
    assert exercise.lead == "فِي"
    assert [option.arabic for option in exercise.options] == ["الْأَرْضِ", "الْأَرْضُ", "الْأَرْضَ"]   # one style for all
    assert exercise.answer_word == "فِي ٱلْأَرْضِ" and exercise.facts == {"case": GENITIVE, "bosnianCase": "L"}
    assert gate.problems(exercise) == []


def test_no_preposition_exercise_when_the_accusative_reads_like_the_genitive_or_the_table_lacks_the_form():
    # A sound plural (and a diptote) writes its accusative like its genitive: two of three options would be one word.
    believers = NounForms("noun:mumin", (_table(PLURAL, DEFINITE, "ٱلْمُؤْمِنُونَ", "ٱلْمُؤْمِنِينَ", "ٱلْمُؤْمِنِينَ"),),
                          (_form("ٱلْمُؤْمِنِينَ", number=PLURAL),))
    unknown = NounForms("noun:ard", (_table(SINGULAR, DEFINITE, "ٱلْأَرْضُ", "ٱلْأَرْضَ", "ٱلْأَرْضِ"),), (_form("أَرْضٍ"),))
    assert preposition_exercises([believers, unknown]) == []


def test_assimilation_marks_of_the_word_before_do_not_hide_the_form():
    lord = NounForms("noun:rabb", (_table(SINGULAR, INDEFINITE, "رَبٌّ", "رَبًّا", "رَبٍّ"),),
                     (_form("رَّبٍّ", state=INDEFINITE, preposition="مِنْ"),))
    (exercise,) = preposition_exercises([lord])
    assert _right(exercise).arabic == "رَبٍّ"


# ---------------------------------------------------------------- adjective agreement

def _adjective(text: str, gender: str, number: str, state: str, case: str) -> AdjectiveForm:
    return AdjectiveForm(text, AdjectiveReading(gender, Cell(number, state, case)))


CLEAR = tuple(_adjective(text, gender, number, state, case) for text, gender, number, state, case in (
    ("مُبِينٌ", MASCULINE, SINGULAR, INDEFINITE, NOMINATIVE), ("مُبِينًا", MASCULINE, SINGULAR, INDEFINITE, ACCUSATIVE),
    ("مُبِينٍ", MASCULINE, SINGULAR, INDEFINITE, GENITIVE), ("الْمُبِينُ", MASCULINE, SINGULAR, DEFINITE, NOMINATIVE),
    ("مُبِينَةٌ", FEMININE, SINGULAR, INDEFINITE, NOMINATIVE), ("مُبِينَةً", FEMININE, SINGULAR, INDEFINITE, ACCUSATIVE),
    ("مُبِينَةٍ", FEMININE, SINGULAR, INDEFINITE, GENITIVE), ("الْمُبِينَةَ", FEMININE, SINGULAR, DEFINITE, ACCUSATIVE),
    ("مُبِينُونَ", MASCULINE, PLURAL, INDEFINITE, NOMINATIVE), ("مُبِينِينَ", MASCULINE, PLURAL, INDEFINITE, ACCUSATIVE),
    ("مُبِينَاتٍ", FEMININE, PLURAL, INDEFINITE, ACCUSATIVE),
))
# كَلِمَاتٍ is a plural of things, read accusative or genitive; كَلَامًا a masculine singular accusative.
NOUNS = {spelling_key("كَلِمَاتٍ"): (NounReading(FEMININE, Cell(PLURAL, INDEFINITE, ACCUSATIVE)),
                                    NounReading(FEMININE, Cell(PLURAL, INDEFINITE, GENITIVE))),
         spelling_key("كَلَامًا"): (NounReading(MASCULINE, Cell(SINGULAR, INDEFINITE, ACCUSATIVE)),)}


def _adjective_sentence(noun: str, adjective: str) -> AdjectiveSentence:
    words = (SentenceWord("قَرَأْتُ", False, B("pročitao sam", "I read")), SentenceWord(noun, False, B("riječi", "words")),
             SentenceWord(adjective, True, B("jasne", "clear")))
    return AdjectiveSentence(word="adjective:mubin", words=words, translation=B("Pročitao sam jasne riječi.", "I read clear words."),
                             forms=CLEAR, sound="audio/s.m4a")


def test_a_plural_of_things_takes_the_feminine_singular_and_no_allowed_form_is_offered_as_wrong():
    (exercise,) = agreement_exercises([_adjective_sentence("كَلِمَاتٍ", "مُبِينَةً")], NOUNS)
    offered = [option.arabic for option in exercise.options]
    assert offered[0] == "مُبِينَةً" and exercise.facts["rule"] == "thingsPlural"
    assert "مُبِينَةٍ" not in offered          # agrees with the genitive reading of كَلِمَاتٍ
    assert "مُبِينَاتٍ" not in offered          # a plural adjective is also good Arabic beside a plural of things
    assert 3 <= len(offered) <= 4 and gate.problems(exercise) == []
    assert [segment.is_blank for segment in exercise.passage] == [False, False, True]
    assert [segment.is_marked for segment in exercise.passage] == [False, True, False]


def test_every_distractor_disagrees_with_every_reading_of_the_noun():
    (exercise,) = agreement_exercises([_adjective_sentence("كَلَامًا", "مُبِينًا")], NOUNS)
    readings = NOUNS[spelling_key("كَلَامًا")]
    for option in exercise.options[1:]:
        form = next(form for form in CLEAR if same_spelling(form.text, option.arabic))
        assert not any(is_allowed(form.reading, noun) for noun in readings)
    assert exercise.facts == {"rule": "masculine", "case": ACCUSATIVE, "state": INDEFINITE}


def test_a_predicate_or_an_unknown_noun_is_not_asked():
    assert agreement_exercises([_adjective_sentence("الطِّفْلُ", "مُبِينٌ")], NOUNS) == []


# ---------------------------------------------------------------- nuances and particles

def _ayah(reference: str, *words: tuple[str, bool]) -> CitedAyah:
    return CitedAyah(reference, tuple(AyahWord(text, hit, f"audio/{text}.m4a" if hit else None) for text, hit in words),
                     B("zašto", "why"))


def test_a_nuance_blank_asks_the_word_the_quran_says_and_skips_an_ayah_cited_twice():
    group = NuanceGroup("nuance:insan-bashar", (
        NuanceMember("إِنْسَان", B("čovjek", "human being"), (_ayah("70:19", ("إِنَّ", False), ("ٱلْإِنسَٰنَ", True)),
                                                               _ayah("17:94", ("بَشَرًا", False), ("رَّسُولًا", False)))),
        NuanceMember("بَشَر", B("smrtnik", "mortal"), (_ayah("17:94", ("بَشَرًا", True), ("رَّسُولًا", False)),)),
    ))
    (exercise,) = nuance_exercises([group])
    assert exercise.reference == "70:19" and _right(exercise).arabic == "إِنْسَان"
    assert [segment.is_blank for segment in exercise.passage] == [False, True]
    assert exercise.answer_word == "ٱلْإِنسَٰنَ" and exercise.answer_sound == "audio/ٱلْإِنسَٰنَ.m4a"
    assert gate.problems(exercise) == []


def test_an_ayah_read_otherwise_in_another_reading_is_never_asked():
    use = ParticleUse("particle:fa", "فَـ", "so-that", B("da bi", "so that"), "SUBJ",
                      (CitedAyah("80:4", (AyahWord("فَتَنفَعَهُ", True),), B("Hafs", "Ḥafṣ"), has_other_reading=True),))
    assert particle_exercises([use]) == []


def test_a_particle_is_asked_among_the_cases_or_among_the_moods():
    did_not = ParticleUse("particle:lam", "لَمْ", "did-not", B("negacija prošlosti", "negating the past"), "JUS",
                          (_ayah("112:3", ("لَمْ", True), ("يَلِدْ", False)),))
    emphasis = ParticleUse("particle:la", "لَـ", "oath", B("zakletva", "oath"), None, (_ayah("102:6", ("لَتَرَوُنَّ", True)),))
    (exercise,) = particle_exercises([did_not, emphasis])
    assert [option.code for option in exercise.options] == ["IND", "SUBJ", "JUS"] and _right(exercise).code == "JUS"
    assert exercise.lead == "لَمْ" and [segment.is_marked for segment in exercise.passage] == [True, False]
    assert gate.problems(exercise) == []


# ---------------------------------------------------------------- shards and JSON

def test_the_shard_hash_is_the_one_the_page_computes():
    # tests/js/exercises.test.mjs holds site/exercises.js to the same values.
    assert [shard_of("noun:ard", 7), shard_of("nuance:insan-bashar", 11), shard_of("particle:fi", 1000)] == [6, 4, 470]


def test_shards_split_by_word_and_list_the_right_option_first():
    exercises = [Exercise(kind=CASE, key=f"k{number}", words=(f"noun:w{number % 5}",),
                          options=(Option(False, code="object"), Option(True, code="subject"))) for number in range(40)]
    split = shards(exercises, max_bytes=500)
    assert len(split) > 1 and sum(len(shard) for shard in split) == 40
    for number, shard in enumerate(split):
        assert all(shard_of(item["words"][0], len(split)) == number for item in shard)
        assert all(item["options"][0] == {"code": "subject"} for item in shard)


def test_the_json_leaves_out_empty_fields_and_marks_positions():
    exercise = Exercise(kind="agreement", key="k", words=("adjective:x",), options=(Option(True, arabic="أ"), Option(False, arabic="ب")),
                        passage=(Segment("ا"), Segment("ب", is_marked=True), Segment("ج", is_blank=True)))
    assert exercise.as_json() == {"id": "k", "words": ["adjective:x"], "options": [{"ar": "أ"}, {"ar": "ب"}],
                                  "passage": ["ا", "ب", "ج"], "marked": [1], "blanks": [2]}


# ---------------------------------------------------------------- pages

TEXTS_KINDS = KINDS


@pytest.fixture(scope="module")
def texts():
    from fil.pages import interface_text
    return interface_text.load()


def test_every_kind_is_named_in_both_languages(texts):
    for code in ("bs", "en"):
        words = texts[code]["exercisePage"]
        assert set(words["kinds"]) == set(TEXTS_KINDS)
        assert len({kind["slug"] for kind in words["kinds"].values()}) == len(TEXTS_KINDS)
        assert set(words["roles"]) == {"subject", "object", "preposition", "possession"}


def test_the_hub_and_a_kind_page_carry_the_script_settings(texts):
    counts = {kind: 3 for kind in TEXTS_KINDS}
    shard_counts = {kind: 2 for kind in TEXTS_KINDS}
    hub = exercise_render.hub_page(BS_EN["bs"], texts, counts, shard_counts, published={"exercises"})
    assert 'id="exercises"' in hub and 'data-language="bs"' in hub and "exercises.js" in hub
    assert 'href="koji-padez/"' in hub and "<noscript>" in hub
    page = exercise_render.kind_page("case", BS_EN["en"], texts, counts, shard_counts, published={"exercises"})
    assert 'data-kinds="case"' in page and "Which case?" in page
    settings = json.loads(re.search(r'data-shards="([^"]+)"', page).group(1).replace("&quot;", '"'))
    assert settings == {"case": 2}
    assert 'hreflang="bs" href="https://jasminguberinic.github.io/quran-verbs/bs/vjezbe/koji-padez/"' in page


def _picture_question(slug: str) -> Exercise:
    return Exercise(kind=PICTURE, key=slug, words=(f"noun:{slug}",), picture=f"pictures/{slug}.svg",
                    options=(Option(True, arabic="أ"), Option(False, arabic="ب")))


def _picture(slug: str, source) -> NounPicture:
    return NounPicture(lemma=slug, root=slug, slug=slug, bosnian=slug, codepoint="1F42A", source=source)


def test_the_pages_that_ask_picture_questions_credit_the_sets_of_their_pictures(texts):
    sets = ExerciseSets({PICTURE: (_picture_question("jamal"), _picture_question("bayt"))})
    pictures = [_picture("jamal", OPENMOJI), _picture("bayt", TWEMOJI), _picture("ard", OWN_DRAWING)]
    credit = exercise_pages.pictures_credit(sets, pictures)
    assert "https://openmoji.org" in credit and "https://github.com/jdecked/twemoji" in credit
    counts, shard_counts = {PICTURE: 2, CASE: 1}, {PICTURE: 1, CASE: 1}
    assert credit in exercise_render.hub_page(BS_EN["bs"], texts, counts, shard_counts, published={"exercises"},
                                              picture_credit=credit)
    assert credit in exercise_render.kind_page(PICTURE, BS_EN["en"], texts, counts, shard_counts,
                                               published={"exercises"}, picture_credit=credit)


def test_no_picture_question_no_picture_credit():
    assert exercise_pages.pictures_credit(ExerciseSets({}), [_picture("jamal", OPENMOJI)]) == ""
    own_drawing_only = ExerciseSets({PICTURE: (_picture_question("ard"),)})
    assert exercise_pages.pictures_credit(own_drawing_only, [_picture("ard", OWN_DRAWING)]) == ""


def test_a_picture_question_whose_picture_no_source_names_fails_the_build():
    with pytest.raises(exercise_pages.UncreditedPicture):
        exercise_pages.pictures_credit(ExerciseSets({PICTURE: (_picture_question("jamal"),)}), [])


def test_a_word_page_links_its_exercises_only_when_there_are_some(texts):
    sets = ExerciseSets({CASE: (Exercise(kind=CASE, key="k", words=("noun:ard",), options=(Option(True, code="subject"),
                                                                                          Option(False, code="object"))),)})
    link = exercise_render.practice_links("noun", sets.words(), texts)
    assert 'href="../../../bs/vjezbe/?w=noun:ard&amp;t=case"' in link("ard", BS_EN["bs"], "../../../")
    assert link("bayt", BS_EN["bs"], "../../../") == ""
    assert link("ard", BS_EN["tr"], "../../../") == ""
