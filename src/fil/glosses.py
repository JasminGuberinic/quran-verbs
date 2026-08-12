"""Does a translation we wrote agree with a lexicon written by someone else?

The morphological layers of the sentence gate prove that the Arabic is real and that
the verb stands in the intended form. They say nothing about the TRANSLATION: a
flawlessly inflected sentence can carry a gloss that quietly means something else,
and no analyzer would object. Since the AI operator writes both the sentence and its
word-by-word gloss, that gloss needs an independent vote.

CAMeL's morphology database supplies one. Every analysis it returns carries an English
gloss written by lexicographers, so asking "does any analysis of this word share a
meaning with what we claim it means?" is a round-trip check — Arabic → their English →
ours — that needs no translation service and stays offline.

Two choices keep it honest rather than decorative:

  - Grammatical words never count as agreement. Without that, "I am" would agree with
    "I create" on the pronoun alone, and the check would pass everything.
  - Words are compared in base form ("knew" ≡ "know", "am" ≡ "is"), because a lexicon
    glosses the lemma while we gloss the inflected word standing in the sentence.

A word the lexicon does not gloss cannot be judged, so it yields None — never False.
Silence is not evidence of a wrong translation.
"""

from __future__ import annotations

import re
from typing import Iterable


def gloss_agrees(ours: str, lexicon: Iterable[str]) -> bool | None:
    """Whether our gloss shares a meaning with any of the lexicon's.

    Returns None when either side carries no meaning-bearing word — there is then
    nothing to compare, and a check that cannot run must not report a failure.
    """
    claimed = content_words(ours)
    attested = {word for gloss in lexicon for word in content_words(gloss)}
    if not claimed or not attested:
        return None
    return bool(claimed & attested)


def content_words(gloss: str) -> frozenset[str]:
    """The meaning-bearing words of an English gloss, reduced to their base form."""
    words = _LETTERS.findall(gloss.lower())
    return frozenset(_base_form(word) for word in words if word not in _GRAMMATICAL)


_LETTERS = re.compile(r"[a-z]+")

# Articles, pronouns, prepositions, conjunctions — plus the feature tags a lexicon
# appends to a gloss ("the+truth+[def.acc.]", "beautiful;nice+two"). None of them
# says what the word MEANS, so agreement on them would be agreement on nothing.
# Auxiliaries (be, do, have) are deliberately absent: they are real verb meanings here.
_GRAMMATICAL = frozenset(
    """
    a an the this that these those
    i me my mine we us our ours you your yours
    he him his she her hers it its they them their theirs
    of to in on at by for with from as into about over under than then here there
    and or but not no nor if so such very
    def indef acc gen nom obj subj poss fem masc sg pl du dual two
    verb noun adj adv pron prep part
    """.split()
)

# Irregular English forms that suffix-stripping cannot bridge. These are exactly the
# highest-frequency verbs — precisely the ones a beginner's sentence is built from —
# so leaving them out would make the check fail on its most important cases.
_IRREGULAR = {
    "am": "be", "is": "be", "are": "be", "was": "be", "were": "be", "been": "be", "being": "be",
    "has": "have", "had": "have", "does": "do", "did": "do", "done": "do",
    "said": "say", "knew": "know", "known": "know", "went": "go", "gone": "go", "goes": "go",
    "made": "make", "took": "take", "taken": "take", "gave": "give", "given": "give",
    "saw": "see", "seen": "see", "came": "come", "wrote": "write", "written": "write",
    "ate": "eat", "eaten": "eat", "found": "find", "told": "tell", "became": "become",
    "heard": "hear", "held": "hold", "kept": "keep", "left": "leave", "meant": "mean",
    "met": "meet", "paid": "pay", "ran": "run", "sat": "sit", "sent": "send", "sold": "sell",
    "stood": "stand", "taught": "teach", "thought": "think", "understood": "understand",
    "brought": "bring", "bought": "buy", "built": "build", "chose": "choose", "chosen": "choose",
    "felt": "feel", "fell": "fall", "spoke": "speak", "spoken": "speak", "won": "win",
    "lost": "lose", "sought": "seek", "struck": "strike", "swore": "swear", "threw": "throw",
    "worshipped": "worship", "worshiped": "worship",
}

_SUFFIXES = ("ing", "es", "ed", "s")


def _base_form(word: str) -> str:
    """A crude but predictable stem: irregulars by table, the rest by suffix."""
    return _stem(_IRREGULAR.get(word, word))


def _stem(word: str) -> str:
    for suffix in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return _without_silent_e(word[: -len(suffix)])
    return _without_silent_e(word)


def _without_silent_e(word: str) -> str:
    """So that "write" and "writing" land on the same stem — but "be" survives."""
    if word.endswith("e") and len(word) >= 5:
        return word[:-1]
    return word
