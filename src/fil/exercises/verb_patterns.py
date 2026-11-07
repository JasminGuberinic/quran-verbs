"""Koji oblik? / Which verb form?: a studied verb's lemma → its form (I–X) shown as number and pattern,
and the other way round: a form → which of four verbs is in it.

Why the right answer is right: the form is the verb card's own (`root_form`, the corpus's and the
Bosnian-checked data); the pattern is the form's textbook pattern on the model root ف ع ل
(`fil.roots.model.verb_pattern`). The learner is shown the verb's root with the lemma, so the
question is only which pattern the root's letters fill.

Why a distractor is wrong: it is another form of the same root family (ten for a three-letter root,
the three a four-letter root has), and it is dropped when its pattern, filled with the verb's own
root, is spelled like the lemma, or when the lemma has the letters the form's shape asks for
(`could_be_in`): such a distractor might be right too. Distractors whose pattern looks closest to the
lemma come first (`looks_closest`), so the learner has to read the letters and not only count them.
In the reverse direction the four verbs are of four different forms, and no distractor verb could be
taken for the asked form.

Pure: the verbs are passed in.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher

from fil.exercises.model import FORM_VERB, VERB_FORM, Exercise, Option
from fil.exercises.text import in_one_style, same_spelling, stable_order
from fil.exercises.vocabulary import Word
from fil.roots.model import verb_pattern

OPTION_COUNT = 4
_MODEL_ROOT = "فعل"
_SHADDA = "ّ"
_ALEF_FORMS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي"})
TRILITERAL_FORMS = tuple(range(1, 11))
QUADRILITERAL_FORMS = (1, 2, 4)
# What each form's past 3rd m.sg. looks like in skeleton letters (`_skeleton`: vowels gone, a doubled letter
# written twice): only the length, the fixed letters and the doubling count, never the radicals.
_SHAPES = {
    1: lambda s: len(s) == 3,
    2: lambda s: len(s) == 4 and s[1] == s[2],
    3: lambda s: (len(s) == 4 and s[1] == "ا") or (len(s) == 3 and s[0] == "ا"),   # the second: آخَذَ, hamza + madda
    4: lambda s: s[0] == "ا" and len(s) in (3, 4),
    5: lambda s: len(s) == 5 and s[0] == "ت" and s[2] == s[3],
    6: lambda s: len(s) == 5 and s[0] == "ت" and s[2] == "ا",
    7: lambda s: len(s) == 5 and s[:2] == "ان",
    8: lambda s: len(s) == 5 and s[0] == "ا" and (s[2] in "تطد" or s[1] == s[2]),
    9: lambda s: len(s) == 5 and s[0] == "ا" and s[3] == s[4],
    10: lambda s: len(s) == 6 and s[:3] == "است",
}


@dataclass(frozen=True)
class FormVerb:
    """A studied verb as these exercises see it: its word, its root and the form it is in."""

    word: Word
    root: str
    form: int

    @property
    def is_quadriliteral(self) -> bool:
        return len(self.root) == 4

    @property
    def available_forms(self) -> tuple[int, ...]:
        return QUADRILITERAL_FORMS if self.is_quadriliteral else TRILITERAL_FORMS

    @property
    def pattern(self) -> str:
        return verb_pattern(self.root, self.form)


def form_code(verb: FormVerb, form: int | None = None) -> str:
    """"2" for a three-letter root's Form II, "q2" for a four-letter root's: the interface's key for the form's note."""
    return f"{'q' if verb.is_quadriliteral else ''}{form or verb.form}"


def verb_form_exercises(verbs: Sequence[FormVerb]) -> list[Exercise]:
    """For each verb: its lemma and root, and its form among three others (the verb's own forms only)."""
    return [exercise for exercise in (_verb_form_exercise(verb) for verb in verbs) if exercise]


def form_verb_exercises(verbs: Sequence[FormVerb]) -> list[Exercise]:
    """For each three-letter verb: its form's number and pattern, and the verb among three of other forms."""
    triliteral = [verb for verb in verbs if not verb.is_quadriliteral]
    return [exercise for exercise in (_form_verb_exercise(verb, triliteral) for verb in triliteral) if exercise]


def could_be_in(verb: FormVerb, form: int) -> bool:
    """A reader could take the verb's lemma for a verb of this form: the form's pattern on the verb's own root is
    spelled like the lemma, or the lemma has the letters the form's shape asks for (`_SHAPES`; the root's own
    letters, weak or not, are not checked). It drops distractors, so it is generous."""
    skeleton = _skeleton(verb.word.arabic)
    if _skeleton(_filled(verb.root, form)) == skeleton:
        return True
    return not verb.is_quadriliteral and _SHAPES[form](skeleton)


def looks_closest(verb: FormVerb, form: int) -> float:
    """How alike the lemma and the form's pattern on the verb's root are, in the letters a reader sees (0–1)."""
    return SequenceMatcher(None, _skeleton(verb.word.arabic), _skeleton(_filled(verb.root, form))).ratio()


# ---------------------------------------------------------------- lemma → form

def _verb_form_exercise(verb: FormVerb) -> Exercise | None:
    others = [form for form in verb.available_forms if form != verb.form and not could_be_in(verb, form)]
    others.sort(key=lambda form: -looks_closest(verb, form))     # stable: the closest-looking first
    chosen = others[:OPTION_COUNT - 1]
    if len(chosen) < min(OPTION_COUNT, len(verb.available_forms)) - 1:
        return None
    options = (_form_option(verb, verb.form, True), *(_form_option(verb, form, False) for form in chosen))
    return Exercise(kind=VERB_FORM, key=verb.word.id.replace(":", "-"), words=(verb.word.id,), options=options,
                    lead=in_one_style(verb.word.arabic), sound=verb.word.sound, answer_sound=verb.word.sound,
                    gloss=verb.word.meaning, facts={"root": " ".join(verb.root), "form": form_code(verb)})


def _form_option(verb: FormVerb, form: int, is_correct: bool) -> Option:
    return Option(is_correct, arabic=verb_pattern(verb.root, form), code=form_code(verb, form))


# ---------------------------------------------------------------- form → verb

def _form_verb_exercise(answer: FormVerb, verbs: Sequence[FormVerb]) -> Exercise | None:
    candidates = [verb for verb in stable_order(verbs, lambda verb: verb.word.id, salt=answer.word.id)
                  if verb.form != answer.form and not could_be_in(verb, answer.form)]
    candidates.sort(key=lambda verb: -looks_closest(verb, answer.form))
    chosen = _verbs_of_other_forms(answer, candidates)
    if len(chosen) < OPTION_COUNT - 1:
        return None
    options = (Option(True, arabic=in_one_style(answer.word.arabic)),
               *(Option(False, arabic=in_one_style(verb.word.arabic)) for verb in chosen))
    return Exercise(kind=FORM_VERB, key=answer.word.id.replace(":", "-"), words=(answer.word.id,), options=options,
                    lead=answer.pattern, answer_sound=answer.word.sound, answer_word=answer.word.arabic,
                    gloss=answer.word.meaning, facts={"form": form_code(answer)})


def _verbs_of_other_forms(answer: FormVerb, candidates: Sequence[FormVerb]) -> list[FormVerb]:
    """Up to three verbs, each of a form no other option is in, none spelled like the answer."""
    chosen: list[FormVerb] = []
    for verb in candidates:
        is_new_form = all(verb.form != taken.form for taken in chosen)
        is_new_word = not any(same_spelling(verb.word.arabic, shown.word.arabic) for shown in (answer, *chosen))
        if is_new_form and is_new_word:
            chosen.append(verb)
        if len(chosen) == OPTION_COUNT - 1:
            break
    return chosen


# ---------------------------------------------------------------- the letters a reader sees

def _filled(root: str, form: int) -> str:
    """The form's pattern with the root's letters in place of ف ع ل (and the fourth radical for a second ل)."""
    letters = iter(root)
    return "".join(next(letters) if character in _MODEL_ROOT else character
                   for character in verb_pattern(root, form))


def _skeleton(word: str) -> str:
    """The letters of a word without vowels, a doubled letter written twice, alif seats and ى folded."""
    letters: list[str] = []
    for character in unicodedata.normalize("NFD", word):
        if character == _SHADDA and letters:
            letters.append(letters[-1])
        elif not unicodedata.category(character).startswith("M"):
            letters.append(character.translate(_ALEF_FORMS))
    return "".join(letters)
