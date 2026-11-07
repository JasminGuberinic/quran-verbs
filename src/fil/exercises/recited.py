"""Čuj učača / Hear the reciter: a Quranic verb form recited, its meaning among four.

The clip is the word as the reciter says it in the ayah (`AttestedForm.sound`); the learner hears no
ayah and sees no Arabic, so the question is only fair where the word alone has one meaning. That is
what `verb_forms.is_askable` already holds for the Quran's forms (no "you"/"she" present, no spelling
that two cells share, no gloss whose object is left open, no other canonical reading), and only forms
glossed in both languages reach it. The right answer is that form's own gloss.

A distractor is the gloss of another form that no reading of the heard word allows (`is_wrong_gloss`):
first forms of the same verb (another person, tense, voice or object), then the commonest form of
verbs about as frequent that are neither of the same root nor a near-synonym nor of overlapping
meaning (`vocabulary.is_fair_distractor`). No two options are one meaning in either language.
After answering the page shows the Arabic form, its grammar and its ayah, linked.

Pure.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence

from fil.exercises.model import HEAR_RECITER, Exercise, Option
from fil.exercises.text import first_distinct, same_gloss, same_spelling, stable_order
from fil.exercises.verb_forms import (DISTRACTORS, AttestedForm, QuranicVerb, _checked, _slug, is_askable, is_wrong_gloss,
                                      quran_form_problems, standing_alone)
from fil.exercises.vocabulary import is_fair_distractor

# The commonest forms of a verb that are asked: a pool of a few thousand over the studied verbs.
FORMS_PER_VERB = 5
# How many other verbs, nearest by frequency, are looked through for distractors.
NEIGHBOUR_VERBS = 40
_RANK_STEP = 25


def hear_reciter_exercises(verbs: Sequence[QuranicVerb], synonyms: Collection[frozenset[str]] = (),
                           per_verb: int = FORMS_PER_VERB) -> list[Exercise]:
    """For each recited, glossed form (the commonest `per_verb` of a verb): its clip, its meaning among four."""
    pool = [standing_alone(verb) for verb in verbs]
    pool = [verb for verb in pool if any(form.sound for form in verb.forms)]
    return [exercise for verb in pool for exercise in
            [found for found in (_hear(verb, form, pool, synonyms) for form in verb.forms if form.sound) if found][:per_verb]]


def _hear(verb: QuranicVerb, answer: AttestedForm, pool: Sequence[QuranicVerb],
          synonyms: Collection[frozenset[str]]) -> Exercise | None:
    if not is_askable(answer, verb.table):
        return None
    salt = f"hear|{verb.table.verb.id}|{answer.arabic}"
    candidates = [*_of_the_same_verb(verb, answer, salt), *_of_nearby_verbs(verb, answer, pool, synonyms, salt)]
    distractors = first_distinct(candidates, DISTRACTORS, lambda form, taken: all(
        not same_gloss(form.gloss, other.gloss) and not same_spelling(form.arabic, other.arabic) for other in taken))
    if len(distractors) < DISTRACTORS:
        return None
    ayah = answer.ayah
    exercise = Exercise(kind=HEAR_RECITER, key=f"{_slug(verb.table)}-{ayah.reference.replace(':', '-')}-{_position_of(answer)}",
                        words=(verb.table.verb.id,), sound=answer.sound,
                        options=(Option(True, meaning=answer.gloss), *(Option(False, meaning=form.gloss) for form in distractors)),
                        reference=ayah.reference, answer_word=answer.arabic, gloss=verb.table.verb.meaning,
                        facts={"readings": answer.grammar.code, "verb": verb.table.verb.arabic})
    return _checked(exercise, _problems(answer, distractors, verb))


def _of_the_same_verb(verb: QuranicVerb, answer: AttestedForm, salt: str) -> list[AttestedForm]:
    return [form for form in stable_order(verb.forms, lambda form: form.arabic, salt=salt)
            if is_wrong_gloss(form, answer, verb.table)]


def _of_nearby_verbs(verb: QuranicVerb, answer: AttestedForm, pool: Sequence[QuranicVerb],
                     synonyms: Collection[frozenset[str]], salt: str) -> list[AttestedForm]:
    """The commonest form of each fair verb about as frequent as the answer's, in a stable order."""
    ranked = sorted(stable_order(pool, lambda other: other.table.verb.id, salt=salt),
                    key=lambda other: abs(other.table.verb.rank - verb.table.verb.rank) // _RANK_STEP)
    fair = [other for other in ranked if is_fair_distractor(verb.table.verb, other.table.verb, synonyms)][:NEIGHBOUR_VERBS]
    return [form for other in fair for form in other.forms[:1] if not same_gloss(form.gloss, answer.gloss)]


def _problems(answer: AttestedForm, distractors: Sequence[AttestedForm], verb: QuranicVerb) -> list[str]:
    """The Quran-form rules hold for the same-verb distractors; no distractor may mean what the answer does."""
    own = [form for form in distractors if form in verb.forms]
    found = quran_form_problems(answer, own, verb.table)
    found += [f"{form.arabic} means what the answer does" for form in distractors if same_gloss(form.gloss, answer.gloss)]
    return found


def _position_of(answer: AttestedForm) -> int:
    return next(index for index, word in enumerate(answer.ayah.words) if word.is_hit)
