"""Picture → word and listen → meaning: the exercises that ask what a word is.

A distractor is another studied word that no learner could fairly take for the right one: not of
the same root (شَجَر beside شَجَرَة), not spelled the same, not sharing a content word of its meaning
in either language (قَلْب "srce" beside فُؤَاد "srce"), not drawn with the same picture, and not a
near-synonym the Nuances section groups with it.

A picture is vaguer than a word: an emoji of grapes is also "fruit", a glass of milk also "a drink",
a calf's face also "a cow", a raincloud also "water", a sun also "a day". So a picture's distractors
come from other kinds of things altogether — never its own category, nor one a picture of it could
pass for (CONFUSABLE_CATEGORIES). A word heard is asked among words of about the same frequency.

Pure: the words are passed in.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass

from fil.exercises.model import LISTEN, PICTURE, WORD_MEANING, Bilingual, Exercise, Option
from fil.exercises.text import first_distinct, in_one_style, meanings_overlap, same_spelling, stable_order
from fil.nouns.categories import is_symbolic

OPTION_COUNT = 4
# Categories (data/noun_categories.json) whose pictures can pass for each other: sky, weather, water and time
# of day; food, drink and fruit. A picture's distractors never come from its own category or one grouped with it.
CONFUSABLE_CATEGORIES = (frozenset({"nature_sky", "water_sea", "time"}), frozenset({"food_drink", "fruit_vegetables"}))


@dataclass(frozen=True)
class Word:
    """A studied word as the vocabulary exercises see it."""

    id: str                      # "noun:ard", "verb:qala"
    arabic: str                  # its dictionary form
    root: str
    meaning: Bilingual
    rank: int                    # its place by frequency among words of its family
    sound: str | None = None     # the checked voice saying it
    picture: str | None = None   # the noun's picture
    emoji: str | None = None     # what the picture was drawn from: two nouns drawn alike are never set side by side
    category: str | None = None  # the noun's category (fruit, body, nature…)

    @property
    def family(self) -> str:
        return self.id.split(":", 1)[0]


def picture_exercises(words: Sequence[Word], synonyms: Collection[frozenset[str]] = ()) -> list[Exercise]:
    """For each word pictured as itself: its picture, and its Arabic word among three others pictured too.

    A symbol (scales for justice) is left out: it would ask the reader to guess the symbol, and a book
    drawn for knowledge would pass for the book."""
    pictured = [word for word in words if word.picture and not is_symbolic(word.category)]
    return [exercise for exercise in (_picture_exercise(word, pictured, synonyms) for word in pictured) if exercise]


def listen_exercises(words: Sequence[Word], synonyms: Collection[frozenset[str]] = ()) -> list[Exercise]:
    """For each voiced word: its sound, and its meaning among three meanings of words of its family."""
    voiced = [word for word in words if word.sound]
    return [exercise for exercise in (_listen_exercise(word, voiced, synonyms) for word in voiced) if exercise]


def word_meaning_exercises(words: Sequence[Word], synonyms: Collection[frozenset[str]] = ()) -> list[Exercise]:
    """For each word: the Arabic written, and its meaning among three meanings of words of its family.

    The same rules as listening (`_meaning_exercise`); nothing is heard before answering, so a learner
    who cannot yet read the word has only the spelling to go on. The word's voice plays after answering."""
    return [exercise for exercise in (_word_meaning_exercise(word, words, synonyms) for word in words) if exercise]


def _word_meaning_exercise(answer: Word, words: Sequence[Word], synonyms: Collection[frozenset[str]]) -> Exercise | None:
    options = _meaning_options(answer, words, synonyms)
    if options is None:
        return None
    return Exercise(kind=WORD_MEANING, key=answer.id.replace(":", "-"), words=(answer.id,), options=options,
                    lead=in_one_style(answer.arabic), answer_sound=answer.sound)


def _picture_exercise(answer: Word, pictured: Sequence[Word], synonyms: Collection[frozenset[str]]) -> Exercise | None:
    candidates = [word for word in stable_order(pictured, lambda word: word.id, salt=answer.id)
                  if not could_be_pictured_alike(answer, word)]
    distractors = _distractors(answer, candidates, synonyms)
    if len(distractors) < OPTION_COUNT - 1:
        return None
    options = (Option(True, arabic=in_one_style(answer.arabic)),
               *(Option(False, arabic=in_one_style(word.arabic)) for word in distractors))
    return Exercise(kind=PICTURE, key=answer.id.split(":", 1)[1], words=(answer.id,), options=options,
                    picture=answer.picture, answer_word=answer.arabic, answer_sound=answer.sound, gloss=answer.meaning)


def _meaning_options(answer: Word, words: Sequence[Word], synonyms: Collection[frozenset[str]]) -> tuple[Option, ...] | None:
    """The answer's meaning among meanings of words of its family about as frequent, or None when too few are fair."""
    family = [word for word in words if word.family == answer.family]
    candidates = stable_order(family, lambda word: word.id, salt=answer.id)
    candidates.sort(key=lambda word: abs(word.rank - answer.rank) // 25)   # stable: words about as frequent first
    distractors = _distractors(answer, candidates, synonyms)
    if len(distractors) < OPTION_COUNT - 1:
        return None
    return (Option(True, meaning=answer.meaning), *(Option(False, meaning=word.meaning) for word in distractors))


def _listen_exercise(answer: Word, voiced: Sequence[Word], synonyms: Collection[frozenset[str]]) -> Exercise | None:
    options = _meaning_options(answer, voiced, synonyms)
    if options is None:
        return None
    return Exercise(kind=LISTEN, key=answer.id.replace(":", "-"), words=(answer.id,), options=options,
                    sound=answer.sound, answer_word=answer.arabic, answer_sound=answer.sound)


def _distractors(answer: Word, candidates: Sequence[Word], synonyms: Collection[frozenset[str]]) -> list[Word]:
    fair = [word for word in candidates if is_fair_distractor(answer, word, synonyms)]
    return first_distinct(fair, OPTION_COUNT - 1,
                          lambda word, taken: all(is_fair_distractor(other, word, synonyms) for other in taken))


def could_be_pictured_alike(answer: Word, other: Word) -> bool:
    """`other` is of `answer`'s category, or of one its picture could pass for (an unknown category is its own)."""
    if answer.category is None or other.category is None:
        return answer.category == other.category
    return any(answer.category in group and other.category in group
               for group in (*CONFUSABLE_CATEGORIES, frozenset({answer.category})))


def is_fair_distractor(answer: Word, other: Word, synonyms: Collection[frozenset[str]] = ()) -> bool:
    """`other` cannot be mistaken for `answer` by a learner who knows both (see the module's rules)."""
    return not (other.id == answer.id
                or other.root == answer.root
                or same_spelling(other.arabic, answer.arabic)
                or meanings_overlap(other.meaning, answer.meaning)
                or (answer.emoji is not None and other.emoji == answer.emoji)
                or any(answer.id in group and other.id in group for group in synonyms))
