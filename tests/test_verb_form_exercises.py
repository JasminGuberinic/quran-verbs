"""Golden tests for the verb-form exercises (Oblik → značenje, Značenje → oblik, Iz Kur'ana): one right
answer by rule, the app's fairness rules (site/practice.js) held equal on both sides, and what is never asked."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from fil.composition.compose import Composed, Skipped, compose_cell
from fil.composition.decomposition import Cell, pgn
from fil.corpus.oracle import table_person
from fil.exercises import gate
from fil.exercises.ayat import AyahWord, CitedAyah
from fil.exercises.model import FORM_MEANING, MEANING_FORM, QURAN_FORM, Bilingual, Exercise, InvalidExercise, Option
from fil.exercises.shards import shards
from fil.exercises.text import is_read_alike, reading_key, same_gloss
from fil.exercises.verb_forms import (AttestedForm, Grammar, Offered, QuranicVerb, TableForm, VerbTable, form_meaning_exercises,
                                      form_meaning_problems, is_wrong_form, meaning_form_exercises, quran_form_exercises)
from fil.exercises.vocabulary import Word
from fil.stages import exercises as stage

B = Bilingual
_PRACTICE_JS = Path(__file__).parents[1] / "src" / "fil" / "site" / "practice.js"

# قَالَ "to say": the table's cells as the card writes them, each with its composed meaning (None: not composed).
_QALA = (
    ("past", "ana", "قُلْتُ", B("rekao sam", "I said")), ("past", "anta", "قُلْتَ", B("rekao si", "you said")),
    ("past", "anti", "قُلْتِ", B("rekla si", "you said")), ("past", "huwa", "قَالَ", B("rekao je", "he/it said")),
    ("past", "hiya", "قَالَتْ", B("rekla je", "she/it said")), ("past", "hum", "قَالُوا", B("rekli su", "they said")),
    ("past", "huma", "قَالَا", B("rekli su", "they (two) said")), ("past", "hunna", "قُلْنَ", B("rekle su", "they said")),
    ("present", "ana", "أَقُولُ", B("kažem", "I say")), ("present", "anta", "تَقُولُ", B("kažeš", "you say")),
    ("present", "hiya", "تَقُولُ", B("kaže", "she/it says")), ("present", "huwa", "يَقُولُ", B("kaže", "he/it says")),
    ("present", "hum", "يَقُولُونَ", B("kažu", "they say")), ("present", "anti", "تَقُولِينَ", None),
    ("imperative", "anta", "قُلْ", B("reci!", "say!")), ("imperative", "antunna", "قُلْنَ", B("recite!", "(you all) say!")),
)


def _table(cells=_QALA, *, word="verb:qala", root="قول", meaning=B("reći", "to say"), rank=1, pattern=1,
           unused=("تَقُولِينَ",)) -> VerbTable:
    forms = tuple(TableForm(Grammar(tense, person), arabic, is_used=arabic not in unused, meaning=gloss, sound=f"{arabic}.m4a")
                  for tense, person, arabic, gloss in cells)
    return VerbTable(Word(word, cells[3][2], root, meaning, rank), pattern, forms)


_KANA = _table((("past", "ana", "كُنْتُ", B("bio sam", "I was")), ("past", "anta", "كُنْتَ", B("bio si", "you were")),
                ("present", "ana", "أَكُونُ", B("jesam", "I am")), ("past", "huwa", "كَانَ", B("bio je", "he/it was")),
                ("past", "hum", "كَانُوا", B("bili su", "they were"))),
               word="verb:kana", root="كون", meaning=B("biti", "to be"), rank=2, unused=())
_TAKALLAMA = _table((("past", "ana", "تَكَلَّمْتُ", B("govorio sam", "I spoke")),
                     ("past", "anta", "تَكَلَّمْتَ", B("govorio si", "you spoke")),
                     ("present", "ana", "أَتَكَلَّمُ", B("govorim", "I speak")),
                     ("past", "huwa", "تَكَلَّمَ", B("govorio je", "he/it spoke"))),
                    word="verb:takallama", root="كلم", meaning=B("govoriti, reći", "to speak, to say"), rank=3, unused=())


def _by_key(exercises: list[Exercise], key: str) -> Exercise:
    return next(exercise for exercise in exercises if exercise.key == key)


def _meanings(exercise: Exercise) -> list[str]:
    return [option.meaning.en for option in exercise.options]


# ---------------------------------------------------------------- the app's rules, held equal on both sides

@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_a_reading_is_what_the_app_calls_one_spelling():
    words = ["قُلْنَ", "تَقُولُ", "ٱدْعُوا۟", "اُدْعُوا", "أَدْعُو", "قَالُوا۟", "قَالُوا", "يَٰمُوسَىٰ", "اِتَّقَوْا"]
    script = (f"const P = require({json.dumps(str(_PRACTICE_JS))});"
              f"process.stdout.write(JSON.stringify({json.dumps(words)}.map(P.spellingKey)))")
    keys = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout)
    assert keys == [reading_key(word) for word in words]
    table = _table()
    card = {"cells": [{"plain": form.arabic, "notUsed": not form.is_used} for form in table.forms]}
    script = (f"const P = require({json.dumps(str(_PRACTICE_JS))}); const card = {json.dumps(card)};"
              "process.stdout.write(JSON.stringify(card.cells.map((cell) => P.readingsOf(card, cell).map((r) => r.plain))))")
    readings = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout)
    used = [index for index, form in enumerate(table.forms) if form.is_used]
    assert [readings[index] for index in used] == [[found.arabic for found in table.readings(table.forms[index].arabic)]
                                                   for index in used]


def test_one_spelling_is_narrower_than_one_option():
    assert is_read_alike("قَالُوا۟", "قَالُوا") and is_read_alike("ٱدْعُوا۟", "اُدْعُوا")
    assert not is_read_alike("أَدْعُو", "اُدْعُوا")      # "I call" is not "call!", though never offered side by side


def test_the_tables_duals_are_masculine_and_a_cell_composes_by_the_quranic_rules():
    assert [pgn(*table_person(person)) for person in ("huwa", "antuma", "huma", "antunna")] == ["3MS", "2D", "3MD", "2FP"]
    paradigm = {"past|act|3MS|-": "rekao je", "imperative|act|2MP|-": "recite!"}
    assert compose_cell("قول|1", Cell("past", "3MS", False), "to say", paradigm) == Composed("he/it said", "rekao je")
    assert compose_cell("قول|1", Cell("imperative", "2MP", False), "to say", paradigm) == Composed("(you all) say!", "recite!")
    assert compose_cell("قول|1", Cell("present", "3MS", False), "to say", paradigm) == Skipped("no paradigm cell")
    assert compose_cell("قضي|1", Cell("past", "3MS", False), "to decree", {"past|act|3MS|-": "odredio je"},
                        polysemous={"قضي|1"}) == Skipped("polysemous verb")
    assert compose_cell("ليس|1", Cell("past", "3MS", False), "to not be", paradigm) == Skipped("idiomatic meaning")


# ---------------------------------------------------------------- Oblik → značenje

def test_a_form_is_asked_with_its_meaning_among_other_cells_of_its_verb():
    asked = _by_key(form_meaning_exercises([_table()]), "qala-past-ana")
    assert asked.kind == FORM_MEANING and asked.lead == "قُلْتُ" and asked.sound == "قُلْتُ.m4a"
    assert asked.correct[0].meaning == B("rekao sam", "I said")
    assert _meanings(asked)[1] == "I say"                 # the same person in another tense comes first
    assert asked.facts == {"readings": "past:ana", "verb": "قَالَ"}
    gate.check([asked])


def test_a_spelling_with_two_readings_is_asked_with_both_and_neither_is_offered_as_wrong():
    exercises = form_meaning_exercises([_table()])
    you_or_she = _by_key(exercises, "qala-present-anta")
    assert you_or_she.correct[0].meaning == B("kažeš / kaže", "you say / she/it says")
    assert "he/it says" not in _meanings(you_or_she)      # "kaže": the she reading's Bosnian
    assert you_or_she.facts["readings"] == "present:anta,present:hiya"
    assert not any(exercise.key == "qala-present-hiya" for exercise in exercises)   # one question per spelling
    said_or_say = _by_key(exercises, "qala-past-hunna")
    assert said_or_say.correct[0].meaning.en == "they said / (you all) say!"
    assert "they (two) said" not in _meanings(said_or_say) and "they said" not in _meanings(said_or_say)[1:]


def test_two_meanings_that_are_one_in_either_language_are_never_offered_together():
    for exercise in form_meaning_exercises([_table()]):
        meanings = [option.meaning for option in exercise.options]
        assert not any(same_gloss(first, second) for index, first in enumerate(meanings) for second in meanings[index + 1:])


def test_a_form_arabic_does_not_use_is_neither_asked_nor_offered():
    exercises = form_meaning_exercises([_table(unused=("تَقُولِينَ", "قُلْتِ"))])
    assert not any(exercise.lead in ("تَقُولِينَ", "قُلْتِ") for exercise in exercises)
    assert not any("rekla si" == option.meaning.bs for exercise in exercises for option in exercise.options)


def test_the_validator_refuses_a_distractor_that_is_a_reading_of_the_shown_form():
    table = _table()
    readings = table.readings("تَقُولُ")
    she = next(form for form in table.forms if form.grammar.code == "present:hiya")
    he = next(form for form in table.forms if form.grammar.code == "present:huwa")
    assert form_meaning_problems(readings[:1], [she]) and form_meaning_problems(readings, [he])
    assert not form_meaning_problems(table.readings("قُلْتُ"), [he])


# ---------------------------------------------------------------- Značenje → oblik

def test_a_meaning_is_asked_with_its_form_among_its_verb_and_the_same_cell_of_another_verb_of_its_pattern():
    asked = _by_key(meaning_form_exercises([_table(), _KANA, _TAKALLAMA]), "qala-past-ana")
    assert asked.kind == MEANING_FORM and asked.translation == B("rekao sam", "I said")
    arabic = [option.arabic for option in asked.options]
    assert arabic[0] == "قُلْتُ" and "كُنْتُ" in arabic             # كَانَ: same pattern, same cell, another meaning
    assert "تَكَلَّمْتُ" not in arabic                              # تَكَلَّمَ "to say" too, and another pattern
    assert asked.answer_word == "قُلْتُ" and asked.answer_sound == "قُلْتُ.m4a"   # heard only after answering
    gate.check([asked])


def test_a_form_whose_spelling_may_say_the_asked_meaning_is_never_offered():
    exercises = meaning_form_exercises([_table(), _KANA])
    she_says = _by_key(exercises, "qala-present-hiya")        # "kaže": he says too
    assert "يَقُولُ" not in [option.arabic for option in she_says.options]
    you_said = _by_key(exercises, "qala-past-anta")           # "you said": قُلْتِ too
    assert "قُلْتِ" not in [option.arabic for option in you_said.options]
    table = _table()
    he_says = next(form for form in table.forms if form.grammar.code == "present:huwa")
    you_say = next(form for form in table.forms if form.grammar.code == "present:anta")
    she = next(form for form in table.forms if form.grammar.code == "present:hiya")
    assert not is_wrong_form(Offered(table, you_say), she)    # تَقُولُ also reads "she says"
    assert is_wrong_form(Offered(table, he_says), you_say)


# ---------------------------------------------------------------- Iz Kur'ana

def _ayah(*words: str, hit: str, reference: str = "1:1") -> CitedAyah:
    return CitedAyah(reference, tuple(AyahWord(word, word == hit) for word in words), B("", ""))


def _form(arabic: str, tense: str, person: str, gloss: Bilingual, *, passive: bool = False, objects: tuple[str, ...] = (),
          reference: str = "") -> AttestedForm:
    reference = reference or f"1:{len(arabic)}{len(gloss.en)}"
    return AttestedForm(arabic, Grammar(tense, person, passive, objects), gloss, _ayah("وَ", arabic, "x", hit=arabic,
                                                                                       reference=reference), f"{arabic}.mp3")


_QURANIC = (
    _form("قَالَ", "past", "huwa", B("rekao je", "he said"), reference="20:19"),
    _form("فَقَالَ", "past", "huwa", B("pa je rekao", "so he said")),             # "so" only: never against قَالَ
    _form("قَالُوا۟", "past", "hum", B("rekli su", "they said")),
    _form("قُلْتُمْ", "past", "antum", B("rekli ste", "you (all) said")),
    _form("قُلْ", "imperative", "anta", B("reci", "say")),
    _form("قِيلَ", "past", "huwa", B("rečeno je", "it was said"), passive=True),   # the other voice: never against قَالَ
    _form("تَقُولُ", "present", "anta", B("kažeš", "you say")),                    # may be "she": never asked
    _form("قَالَهَا", "past", "huwa", B("ju je rekao", "he said it"), objects=("hiya",)),   # opens with an enclitic
)


def test_a_quranic_form_is_asked_in_its_ayah_among_glosses_of_other_cells_of_its_verb():
    exercises = quran_form_exercises([QuranicVerb(_table(), _QURANIC)])
    asked = _by_key(exercises, "qala-20-19-1")
    assert asked.kind == QURAN_FORM and asked.correct[0].meaning.en == "he said"
    assert [segment.is_marked for segment in asked.passage] == [False, True, False]
    assert asked.answer_word == "قَالَ" and asked.answer_sound == "قَالَ.mp3" and asked.reference == "20:19"
    offered = _meanings(asked)[1:]
    assert "so he said" not in offered and "it was said" not in offered and "he said it" not in offered
    assert not any(exercise.answer_word in ("تَقُولُ", "قَالَهَا") for exercise in exercises)
    gate.check(exercises)


def test_a_long_ayah_is_not_asked_and_a_verb_is_asked_at_most_so_often():
    long_ayah = AttestedForm("قَالَ", Grammar("past", "huwa"), B("rekao je", "he said"),
                             _ayah(*(["x"] * 40), "قَالَ", hit="قَالَ"))
    assert quran_form_exercises([QuranicVerb(_table(), (long_ayah, *_QURANIC[2:5]))])[0].answer_word != "قَالَ"
    assert len(quran_form_exercises([QuranicVerb(_table(), _QURANIC)], per_verb=1)) == 1


def test_the_gate_lets_one_verbs_meanings_share_words_but_never_be_one_meaning():
    options = (Option(True, meaning=B("rekao je", "he said")), Option(False, meaning=B("rekli su", "they said")))
    gate.check([Exercise(kind=QURAN_FORM, key="k", words=("verb:qala",), options=options)])
    with pytest.raises(InvalidExercise):
        gate.check([Exercise(kind="listen", key="k", words=("verb:qala",), options=options)])
    with pytest.raises(InvalidExercise):
        gate.check([Exercise(kind=FORM_MEANING, key="k", words=("verb:qala",),
                             options=(Option(True, meaning=B("rekao si", "you said")), Option(False, meaning=B("rekla si", "you said"))))])


# ---------------------------------------------------------------- the stage's adapter and the files

def _card() -> dict:
    hit = {"text": "قَالَ", "hit": True, "audio": "a.m4a", "gloss": {"bs": "rekao je", "en": "he said", "tr": "dedi"}}
    return {"root": "قول", "form": 1, "meaning": {"bs": "reći", "en": "to say"},
            "cells": [{"tense": "past", "pronoun": "huwa", "plain": "قَالَ", "notUsed": False, "spoken": "s.m4a"}],
            "ayat": [{"ref": "20:19", "words": [hit, {"text": "أَلْقِهَا", "hit": False}],
                      "translation": {"en": {"text": "He said: Cast it down", "by": "Pickthall"}}}],
            "forms": [{"arabic": "قَالَ", "first": "2:30", "audio": "w.m4a", "gloss": {"bs": "rekao je", "en": "he said"},
                       "grammar": [{"tense": "past", "pronoun": "huwa", "passive": False, "objects": []}]},
                      {"arabic": "يَقُولُ", "first": "2:8", "gloss": {"en": "he says"},       # no Bosnian: not asked
                       "grammar": [{"tense": "present", "pronoun": "huwa", "passive": False, "objects": []}]},
                      {"arabic": "قُلْنَا", "first": "2:34", "gloss": {"bs": "rekli smo", "en": "we said"},
                       "grammar": [{"tense": "past", "pronoun": "nahnu", "passive": False, "objects": []}]}]}


def test_the_stage_reads_a_card_into_tables_and_quranic_forms():
    sources = stage.Sources(emoji={}, categories={}, noun_readings={}, bosnian={},
                            paradigms={"قول|1": {"past|act|3MS|-": "rekao je"}},
                            ayat={"2:34": ("وَإِذْ", "قُلْنَا", "لِلْمَلَٰٓئِكَةِ")})
    word = stage._verb_word("qala", {**_card(), "lemma": "قَالَ", "rank": 1})
    table = stage._verb_table(word, _card(), sources)
    assert table.forms[0].meaning == B("rekao je", "he/it said") and table.forms[0].sound == "s.m4a"
    verb = stage._quranic_verb(table, _card(), sources)
    assert [form.arabic for form in verb.forms] == ["قَالَ", "قُلْنَا"]
    said, we_said = verb.forms
    assert said.ayah.reference == "20:19" and said.ayah.translation.by == "Pickthall"    # the example, glossed alike
    assert we_said.ayah.reference == "2:34" and [word.is_hit for word in we_said.ayah.words] == [False, True, False]


def test_a_word_with_many_questions_does_not_crowd_a_file():
    def sized(word: str, key: str, length: int) -> Exercise:
        return Exercise(kind=QURAN_FORM, key=key, words=(word,), options=(
            Option(True, meaning=B("a" * length, "a")), Option(False, meaning=B("b", "b"))))
    heavy = [sized("verb:heavy", f"h{number}", 500) for number in range(10)]
    light = [sized(f"verb:w{number}", f"l{number}", 100) for number in range(40)]
    split = shards([*heavy, *light], max_bytes=5_000)
    sizes = [len(json.dumps(shard, ensure_ascii=False, separators=(",", ":")).encode()) for shard in split]
    assert len(split) > 3 and max(sizes) <= 5_000 * 1.25          # the size alone asks for 3; uneven hashing for more
    assert sum(len(shard) for shard in split) == 50


def test_a_verb_page_links_its_own_exercises_as_a_verb():
    from fil.languages import LANGUAGES
    from fil.pages import exercise_render, interface_text
    from fil.stages.exercises import ExerciseSets
    asked = form_meaning_exercises([_table()])
    link = exercise_render.practice_links("verb", ExerciseSets({FORM_MEANING: tuple(asked)}).words(), interface_text.load())
    languages = {language.code: language for language in LANGUAGES}
    bosnian = link("qala", languages["bs"], "../../")
    assert "Vježbaj ovaj glagol" in bosnian and 'href="../../bs/vjezbe/?w=verb:qala&amp;t=form-meaning"' in bosnian
    assert "Practise this verb" in link("qala", languages["en"], "../../") and link("qala", languages["fr"], "../../") == ""


# ---------------------------------------------------------------- a referent or a sense the ayah decides

_SAID_HIM_OR_IT = _form("قَالَهُ", "past", "huwa", B("rekao ga je", "he said him/it"), objects=("huwa",), reference="9:9")


def test_a_gloss_that_leaves_its_object_open_is_never_asked_from_the_quran():
    """سَخَّرَهَا is the camels in 22:37 and the wind in 69:7: "he subjected her/it" is not what either ayah says."""
    exercises = quran_form_exercises([QuranicVerb(_table(), (*_QURANIC, _SAID_HIM_OR_IT))])
    assert not any(exercise.answer_word == "قَالَهُ" for exercise in exercises)
    resolved = AttestedForm("قَالَهُ", _SAID_HIM_OR_IT.grammar, B("rekao ga je", "he said it"), _SAID_HIM_OR_IT.ayah)
    asked = [exercise for exercise in quran_form_exercises([QuranicVerb(_table(), (*_QURANIC, resolved))])
             if exercise.answer_word == "قَالَهُ"]
    assert [exercise.correct[0].meaning.en for exercise in asked] == ["he said it"]


def test_a_form_is_asked_with_the_gloss_of_the_place_it_is_shown_in():
    """A polysemous verb's form in two senses, or a referent resolved place by place: the question shows one
    ayah, so its answer is that place's gloss, not the form's row."""
    card = _card()
    card["forms"][2]["gloss"] = {"bs": "rekli smo; kazali smo", "en": "we said; we told"}
    sources = stage.Sources(emoji={}, categories={}, noun_readings={}, bosnian={},
                            paradigms={"قول|1": {"past|act|3MS|-": "rekao je"}},
                            ayat={"2:34": ("وَإِذْ", "قُلْنَا", "لِلْمَلَٰٓئِكَةِ")},
                            place_glosses={("2:34", "قُلْنَا"): B("kazali smo", "we told")})
    word = stage._verb_word("qala", {**card, "lemma": "قَالَ", "rank": 1})
    verb = stage._quranic_verb(stage._verb_table(word, card, sources), card, sources)
    assert verb.forms[1].gloss == B("kazali smo", "we told") and verb.forms[1].ayah.reference == "2:34"


def test_a_word_glossed_two_ways_in_one_ayah_has_no_place_gloss():
    from fil.study import QuranWord
    ayat = {(2, 34): (QuranWord(2, 34, 1, "قُلْنَا"), QuranWord(2, 34, 2, "x"), QuranWord(2, 34, 3, "قُلْنَا")),
            (2, 35): (QuranWord(2, 35, 1, "قُلْنَا"),)}
    glosses = {"2:34:1": {"en": "we said", "bs": "rekli smo"}, "2:34:3": {"en": "we told", "bs": "kazali smo"},
               "2:35:1": {"en": "we told", "bs": "kazali smo"}}
    assert stage.place_glosses(glosses, ayat) == {("2:35", "قُلْنَا"): B("kazali smo", "we told")}


# ---------------------------------------------------------------- Čuj učača / Hear the reciter

def test_a_recited_form_is_asked_by_its_clip_alone_among_meanings_that_cannot_be_it():
    from fil.exercises.recited import hear_reciter_exercises
    kana = QuranicVerb(_KANA, (_form("كَانَ", "past", "huwa", B("bio je", "he was"), reference="2:10"),))
    exercises = hear_reciter_exercises([QuranicVerb(_table(), _QURANIC), kana])
    asked = _by_key(exercises, "qala-20-19-1")
    assert asked.kind == "hear-reciter" and asked.sound == "قَالَ.mp3" and not asked.passage
    assert asked.correct[0].meaning.en == "he said" and asked.reference == "20:19"
    assert asked.facts["readings"] == "past:huwa"
    offered = _meanings(asked)
    assert len(offered) == 4 and len(set(offered)) == 4
    assert "so he said" not in offered and "it was said" not in offered      # never a reading of the word heard
    assert not any(exercise.answer_word in ("تَقُولُ", "قَالَهَا") for exercise in exercises)
    gate.check(exercises)


def test_a_recited_form_without_a_clip_or_enough_distractors_is_not_asked():
    from fil.exercises.recited import hear_reciter_exercises
    silent = AttestedForm("قَالَ", Grammar("past", "huwa"), B("rekao je", "he said"), _ayah("x", "قَالَ", hit="قَالَ"))
    assert hear_reciter_exercises([QuranicVerb(_table(), (silent, *_QURANIC[2:5]))])[0].answer_word != "قَالَ"
    assert hear_reciter_exercises([QuranicVerb(_table(), _QURANIC[:2])]) == []
