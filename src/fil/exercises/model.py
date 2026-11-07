"""What an exercise is: a question, its options, and what the learner is shown after answering.

Pure data. An exercise is built at build time from content that has already passed its own gate
(a noun's checked case table, a reviewed practice sentence, an ayah the corpus places a word in),
never from Arabic made up for the exercise. Its options are of one sort — Arabic words to pick, a
meaning in Bosnian and English, or a grammatical answer the interface names (`code`, e.g. the role
"subject" or the effect "JUS") — and exactly one of them is right (fil.exercises.gate says so).

The JSON a page reads lists the right option first; the page shuffles them.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

# The kinds of exercise, in the order the hub shows them.
PICTURE = "picture"           # a noun's picture → its Arabic word
ANIMATION = "animation"       # a verb's animation → the verb, its Arabic with its meaning
LISTEN = "listen"             # a word heard → its meaning
CASE = "case"                 # a noun marked in a practice sentence → its case and why
PREPOSITION = "preposition"   # a preposition from the Quran → the ending of the noun after it
AGREEMENT = "agreement"       # a noun in a sentence → the adjective form that agrees with it
NUANCE = "nuance"             # an ayah with a blank → which of the near-synonyms the Quran says there
PARTICLE = "particle"         # a particle in an ayah → what it does to the next word
FORM_MEANING = "form-meaning" # a verb form of the table, heard → its meaning (who, when)
MEANING_FORM = "meaning-form" # a meaning → the verb form that says it
QURAN_FORM = "quran-form"     # a verb form marked in an ayah → its gloss
HEAR_RECITER = "hear-reciter" # a verb form as a real reciter says it → its meaning
WORD_MEANING = "word-meaning" # a noun or adjective written → its meaning
VERB_FORM = "verb-form"       # a verb's lemma → which of the ten forms it is
FORM_VERB = "form-verb"       # a form (number and pattern) → which of four verbs is in it
KINDS = (PICTURE, ANIMATION, LISTEN, WORD_MEANING, FORM_MEANING, MEANING_FORM, QURAN_FORM, HEAR_RECITER, VERB_FORM, FORM_VERB, CASE,
         PREPOSITION, AGREEMENT, NUANCE, PARTICLE)
# The kinds whose meaning options are forms of one verb: they differ by person and tense ("rekao je" /
# "rekli su"), so they may share words; two of them that are the same meaning may not be offered.
ONE_VERB_MEANINGS = (FORM_MEANING, QURAN_FORM, HEAR_RECITER)

# The word families an exercise is about, as its word ids name them ("noun:ard"), so a word's page
# can link the exercises about that word.
NOUN_WORD, ADJECTIVE_WORD, VERB_WORD, NUANCE_WORD, PARTICLE_WORD = "noun", "adjective", "verb", "nuance", "particle"
WORD_FAMILIES = (NOUN_WORD, ADJECTIVE_WORD, VERB_WORD, NUANCE_WORD, PARTICLE_WORD)


class InvalidExercise(ValueError):
    """An exercise that must not reach a learner; the message names every problem."""


@dataclass(frozen=True)
class Bilingual:
    """A learner-facing text in both languages the exercises are written in."""

    bs: str
    en: str

    def as_json(self) -> dict[str, str]:
        return {"bs": self.bs, "en": self.en}


@dataclass(frozen=True)
class QuranTranslation:
    """A published translation of an ayah, shown as it is, with its translator (English only, for now)."""

    text: str
    by: str

    def as_json(self) -> dict[str, str]:
        return {"text": self.text, "by": self.by}


@dataclass(frozen=True)
class Option:
    """One answer to choose: an Arabic word (with its meaning beside it, where the kind names the word
    by both), a meaning, or a grammatical answer named by `code`."""

    is_correct: bool
    arabic: str | None = None
    meaning: Bilingual | None = None
    code: str | None = None

    @property
    def sort(self) -> str:
        """Which of the three sorts of option this is."""
        if self.arabic is not None:
            return "arabic"
        if self.meaning is not None:
            return "meaning"
        return "code"

    def as_json(self) -> dict[str, str]:
        if self.arabic is not None and self.meaning is not None:
            return {"ar": self.arabic, **self.meaning.as_json()}
        if self.arabic is not None:
            # A verb form is offered as its pattern, with the form it is the pattern of.
            return {"ar": self.arabic, "code": self.code} if self.code else {"ar": self.arabic}
        if self.meaning is not None:
            return self.meaning.as_json()
        return {"code": self.code or ""}


@dataclass(frozen=True)
class Segment:
    """A word of a sentence or an ayah: marked (the word asked about) or blanked (the word to find)."""

    text: str
    is_marked: bool = False
    is_blank: bool = False


@dataclass(frozen=True)
class Exercise:
    """One question. `key` is unique within its kind; `words` are the word ids it practises.

    Before answering the learner sees the picture (or watches the `animation`, an inline SVG), hears `sound`, reads the `passage` (with
    `lead`: the preposition said before the options, or the particle asked about) and its `translation`. After
    answering: the `explanation`, the `answer_word` (the form the Quran itself says) with its
    `answer_sound`, the word's `gloss`, and `facts` — grammatical codes the interface puts into
    words (case, Bosnian case, the agreement rule)."""

    kind: str
    key: str
    words: tuple[str, ...]
    options: tuple[Option, ...]
    picture: str | None = None
    animation: str | None = None
    sound: str | None = None
    passage: tuple[Segment, ...] = ()
    reference: str | None = None
    lead: str | None = None
    translation: Bilingual | None = None
    quran_translation: QuranTranslation | None = None
    explanation: Bilingual | None = None
    answer_word: str | None = None
    answer_sound: str | None = None
    gloss: Bilingual | None = None
    facts: Mapping[str, str] = field(default_factory=dict)

    @property
    def identity(self) -> str:
        return f"{self.kind}:{self.key}"

    @property
    def correct(self) -> tuple[Option, ...]:
        return tuple(option for option in self.options if option.is_correct)

    def as_json(self) -> dict[str, object]:
        """The compact form a page reads: the right option first, empty fields left out."""
        ordered = [*self.correct, *(option for option in self.options if not option.is_correct)]
        shown: dict[str, object] = {"id": self.key, "words": list(self.words),
                                    "options": [option.as_json() for option in ordered]}
        optional = {"picture": self.picture, "animation": self.animation, "sound": self.sound, "ref": self.reference, "lead": self.lead,
                    "answerWord": self.answer_word, "answerSound": self.answer_sound}
        shown.update({name: value for name, value in optional.items() if value})
        texts = {"translation": self.translation, "quranTranslation": self.quran_translation,
                 "explanation": self.explanation, "gloss": self.gloss}
        shown.update({name: value.as_json() for name, value in texts.items() if value})
        if self.passage:
            shown.update(_passage_json(self.passage))
        if self.facts:
            shown["facts"] = dict(self.facts)
        return shown


def _passage_json(passage: tuple[Segment, ...]) -> dict[str, list]:
    """The passage's words, and the positions of the marked and blanked ones (compact: a file holds hundreds)."""
    shown: dict[str, list] = {"passage": [segment.text for segment in passage]}
    marked = [position for position, segment in enumerate(passage) if segment.is_marked]
    blanks = [position for position, segment in enumerate(passage) if segment.is_blank]
    if marked:
        shown["marked"] = marked
    if blanks:
        shown["blanks"] = blanks
    return shown


def word_id(family: str, slug: str) -> str:
    """"noun:ard" — a word's id across the exercise kinds."""
    if family not in WORD_FAMILIES:
        raise InvalidExercise(f"unknown word family {family!r}")
    return f"{family}:{slug}"
