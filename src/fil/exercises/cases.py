"""Koji padež? / Which case? — a noun marked in one of its practice sentences: which case, and why.

The sentences are the noun cards' own, each written for one role and passed by the noun sentence
gate (fil.nouns.sentence_gate), which holds the marked word to its case table: the subject is
nominative, the object accusative, a noun after a preposition and the possessor of an iḍāfa
genitive. The four answers are those four (case, reason) pairs, so exactly one is right — the
role the sentence was written and checked for. The learner is shown, after answering, how the
word is said in Bosnian in that very sentence.

Pure.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from fil.exercises.model import CASE, Bilingual, Exercise, Option, Segment
from fil.nouns.sentence_gate import ROLE_CASES, ROLES


@dataclass(frozen=True)
class SentenceWord:
    arabic: str
    is_target: bool
    gloss: Bilingual


@dataclass(frozen=True)
class NounSentence:
    """One reviewed practice sentence of a studied noun, written for `role`."""

    word: str                    # "noun:bayt"
    role: str                    # fil.nouns.sentence_gate.ROLES
    words: tuple[SentenceWord, ...]
    translation: Bilingual
    sound: str | None = None


def case_exercises(sentences: Sequence[NounSentence]) -> list[Exercise]:
    return [_exercise(sentence) for sentence in sentences if _is_askable(sentence)]


def _is_askable(sentence: NounSentence) -> bool:
    """A known role, and exactly one marked word to ask about."""
    return sentence.role in ROLES and sum(1 for word in sentence.words if word.is_target) == 1


def _exercise(sentence: NounSentence) -> Exercise:
    target = next(word for word in sentence.words if word.is_target)
    options = tuple(Option(role == sentence.role, code=role) for role in ROLES)
    return Exercise(kind=CASE, key=f"{sentence.word.split(':', 1)[1]}-{sentence.role}", words=(sentence.word,),
                    options=options, passage=tuple(Segment(word.arabic, is_marked=word.is_target) for word in sentence.words),
                    translation=sentence.translation, answer_sound=sentence.sound, gloss=target.gloss,
                    facts={"case": ROLE_CASES[sentence.role], "role": sentence.role})
