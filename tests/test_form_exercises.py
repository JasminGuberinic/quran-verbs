"""Koji oblik? / Which verb form?, Oblik → glagol, and Riječ → značenje: one right answer, fair distractors."""

from __future__ import annotations

from fil.exercises import gate
from fil.exercises.model import Bilingual, Exercise, Option, word_id
from fil.exercises.text import in_one_style
from fil.exercises.verb_patterns import FormVerb, could_be_in, form_verb_exercises, verb_form_exercises
from fil.exercises.vocabulary import Word, word_meaning_exercises


def _word(slug: str, arabic: str, root: str, bs: str, en: str, rank: int, family: str) -> Word:
    return Word(id=word_id(family, slug), arabic=arabic, root=root, meaning=Bilingual(bs, en), rank=rank,
                sound=f"audio/{slug}.m4a")


def _right(exercise: Exercise) -> Option:
    (right,) = exercise.correct
    return right


def _verb(slug: str, arabic: str, root: str, form: int) -> FormVerb:
    return FormVerb(_word(slug, arabic, root, slug, slug, 1, "verb"), root, form)


VERBS = [_verb("katab", "كَتَبَ", "كتب", 1), _verb("allam", "عَلَّمَ", "علم", 2), _verb("qatal", "قَاتَلَ", "قتل", 3),
         _verb("arsal", "أَرْسَلَ", "رسل", 4), _verb("takabbar", "تَكَبَّرَ", "كبر", 5),
         _verb("intasar", "اِنْتَصَرَ", "نصر", 8), _verb("istaghfar", "اِسْتَغْفَرَ", "غفر", 10),
         _verb("qala", "قَالَ", "قول", 1)]


def test_a_verb_is_asked_its_own_form_among_forms_it_cannot_be_taken_for():
    built = {exercise.key: exercise for exercise in verb_form_exercises(VERBS)}
    assert len(built) == len(VERBS)
    arsal = built["verb-arsal"]
    assert arsal.lead == "أَرْسَلَ" and arsal.sound and arsal.facts == {"root": "ر س ل", "form": "4"}
    assert _right(arsal).arabic == "أَفْعَلَ" and _right(arsal).code == "4"
    for verb in VERBS:
        exercise = built[verb.word.id.replace(":", "-")]
        assert _right(exercise).code == str(verb.form) and len(exercise.options) == 4
        assert not any(could_be_in(verb, int(option.code)) for option in exercise.options[1:])
        assert gate.problems(exercise) == []


def test_a_lemma_that_is_spelled_like_two_forms_never_has_the_other_as_a_distractor():
    amana = _verb("amana", "آمَنَ", "أمن", 4)    # three letters like a Form I, hamza + madda
    assert could_be_in(amana, 1) and could_be_in(amana, 4)
    (exercise,) = verb_form_exercises([amana])
    assert "1" not in {option.code for option in exercise.options}


def test_a_four_letter_root_is_asked_among_its_own_three_forms():
    (exercise,) = verb_form_exercises([_verb("waswas", "وَسْوَسَ", "وسوس", 1)])
    assert _right(exercise).code == "q1" and len(exercise.options) == 3
    assert {option.arabic for option in exercise.options} == {"فَعْلَلَ", "تَفَعْلَلَ", "اِفْعَلَلَّ"}
    assert gate.problems(exercise) == []


def test_which_verb_is_in_a_form_gives_four_verbs_of_four_forms_and_none_it_could_be():
    built = form_verb_exercises(VERBS)
    by_arabic = {in_one_style(verb.word.arabic): verb for verb in VERBS}
    assert built
    for exercise in built:
        shown = [by_arabic[option.arabic] for option in exercise.options]
        assert len({verb.form for verb in shown}) == 4
        assert exercise.lead == shown[0].pattern and exercise.facts == {"form": str(shown[0].form)}
        assert not any(could_be_in(verb, shown[0].form) for verb in shown[1:])
        assert gate.problems(exercise) == []


def test_without_four_verbs_of_other_forms_nothing_is_asked():
    assert form_verb_exercises(VERBS[:3]) == []
    assert form_verb_exercises([_verb("waswas", "وَسْوَسَ", "وسوس", 1)]) == []   # a four-letter root has no pattern to ask


def test_word_meaning_asks_the_written_word_among_meanings_of_its_family_only():
    rows = [("كَبِير", "كبر", "velik", "big"), ("صَغِير", "صغر", "mali", "small"), ("قَرِيب", "قرب", "blizak", "near"),
            ("بَعِيد", "بعد", "daleko", "far"), ("عَظِيم", "عظم", "velik, silan", "great")]
    adjectives = [_word(f"a{rank}", arabic, root, bs, en, rank, "adjective")
                  for rank, (arabic, root, bs, en) in enumerate(rows, start=1)]
    heart = _word("qalb", "قَلْب", "قلب", "srce", "heart", 1, "noun")
    built = {exercise.key: exercise for exercise in word_meaning_exercises([heart, *adjectives])}
    big = built["adjective-a1"]
    assert big.lead == "كَبِير" and _right(big).meaning == Bilingual("velik", "big") and big.sound is None
    assert big.answer_sound == "audio/a1.m4a"
    assert Bilingual("velik, silan", "great") not in {option.meaning for option in big.options}   # shares "velik"
    assert "heart" not in {option.meaning.en for option in big.options}                            # adjectives only
    assert "noun-qalb" not in built                                                               # one noun: no foils
    assert all(gate.problems(exercise) == [] for exercise in built.values())
