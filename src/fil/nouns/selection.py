"""Which nouns are taught next: the most frequent ones a case table can teach.

A batch takes lemmas by frequency, but not every frequent "noun" of the corpus is a noun
a learner declines. Skipped, each for a reason a learner would recognise:

  - adverbs of place and time (بَيْنَ, عِندَ) and the nouns used as such (قَبْلَ, بَعْدَ,
    دُونَ) — they are learned as prepositions, with no case table of their own;
  - quantifiers and pronoun-like words (كُلّ, بَعْض, أَيّ, غَيْر, كَيْفَ) — they decline,
    but what they mean is their construction, not a thing;
  - adjectives — they come in a phase of their own, with agreement (docs/NOUNS-PLAN.md);
  - proper names — a list of their own, no case table.

Pure.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from fil.nouns.model import ADJECTIVE, ADVERB, PROPER_NOUN, NounLemma

# Lemmas the corpus files as nouns that are taught as particles or constructions instead.
NOT_TAUGHT_AS_NOUNS: dict[str, str] = {
    "كُلّ": "quantifier", "بَعْض": "quantifier", "أَيّ": "pronoun-like", "غَيْر": "pronoun-like",
    "قَبْل": "adverb", "بَعْد": "adverb", "دُون": "adverb", "كَيْف": "interrogative",
    "آخِر": "adjective-like", "أَوَّل": "adjective-like", "مِثْل": "pronoun-like", "سَوْف": "particle",
    "لَدُن": "adverb", "فَوْق": "adverb", "تَحْت": "adverb", "حَوْل": "adverb", "أَمام": "adverb",
    "خَلْف": "adverb", "وَراء": "adverb", "حَيْث": "adverb", "إِذْ": "adverb", "إِذا": "adverb",
    "مَعَ": "adverb", "شَطْر": "adverb", "سُبْحان": "exclamation", "أَيْن": "interrogative", "أَنَّى": "interrogative",
}
_NOT_TAUGHT_KINDS = {ADVERB: "adverb", ADJECTIVE: "adjective", PROPER_NOUN: "proper name"}


def skip_reason(lemma: NounLemma) -> str | None:
    """Why this lemma gets no noun card, or None when it does."""
    return _NOT_TAUGHT_KINDS.get(lemma.kind) or NOT_TAUGHT_AS_NOUNS.get(lemma.lemma)


def next_nouns(lemmas: Sequence[NounLemma], count: int, studied: Iterable[str],
               held_back: Iterable[str] = ()) -> tuple[list[NounLemma], list[tuple[NounLemma, str]]]:
    """The `count` most frequent teachable lemmas not yet studied, and those skipped on the way.

    `studied` and `held_back` are "lemma|root" keys; a held-back lemma (a content-policy
    question for the owner) is skipped with that reason.
    """
    done, held = set(studied), set(held_back)
    chosen: list[NounLemma] = []
    skipped: list[tuple[NounLemma, str]] = []
    for lemma in lemmas:
        if len(chosen) == count:
            break
        key = f"{lemma.lemma}|{lemma.root}"
        if key in done:
            continue
        reason = "held back for the owner" if key in held else skip_reason(lemma)
        if reason:
            skipped.append((lemma, reason))
            continue
        chosen.append(lemma)
    return chosen, skipped
