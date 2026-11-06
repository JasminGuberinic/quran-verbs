"""Read the pronouns of the Quran a learner meets as words of their own, named as a grammar names them.

The corpus gives the independent personal pronouns no lemma, and files every demonstrative under
one lemma (ذا) and every relative under one (الَّذِي); a learner looks for هُوَ, ذَٰلِكَ and الَّذِينَ.
So each is named here by its citation form, from what the corpus does give:

    2:29:1:1   هُوَ        N   PRON|3MS                   person, gender, number   → هُوَ
    2:2:1:1    ذَٰ + لِ + كَ  N   DEM|LEM:ذا|MS, DIST, ADDR   far (the كَ of address) → ذَٰلِكَ
    2:25:20    هَٰ + ذَا     N   ATT, DEM|LEM:ذا|MS          near (the هَا of attention) → هَٰذَا
    1:7:2:1    ٱلَّذِينَ     N   REL|LEM:الَّذِي|MP           gender and number       → الَّذِينَ
    1:5:1:1    إِيَّاكَ      N   PRON|LEM:إِيّا|2MS            its own lemma           → إِيّا

A pronoun the corpus segments after a preposition (لَهُمْ: لَ + هُمْ) is attached, not independent,
and is not read; neither is a suffix (رَزَقْنَٰهُمْ). A demonstrative with neither the هَا of attention
nor the كَ of address (مَن ذَا) keeps the corpus's lemma. Each occurrence is a ParticleOccurrence
(the pronoun pages are built by the particle engine) filed under the corpus's tag: PRON, DEM, REL.
Pure: segments in.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from itertools import groupby

from fil.corpus.parse import Segment
from fil.corpus.particles import NOUN, PARTICLE, corpus_tag, lemma_of, marker_after
from fil.particles.model import ParticleOccurrence

PRONOUN, DEMONSTRATIVE, RELATIVE = "PRON", "DEM", "REL"
_SUFFIX, _PREPOSITION, _ATTENTION, _ADDRESS = "SUFF", "P", "ATT", "ADDR"
# The corpus writes the shadda before the fatḥa: ٱلَّذِي as the corpus spells its lemma.
_DEMONSTRATIVE_LEMMA, _RELATIVE_LEMMA = "ذا", "\u0627\u0644\u0651\u064e\u0630\u0650\u064a"
_NUMBERS = frozenset({"MS", "FS", "MP", "FP", "MD", "FD", "P", "D"})

PERSONAL = {"3MS": "هُوَ", "3FS": "هِيَ", "3D": "هُمَا", "3MP": "هُمْ", "3FP": "هُنَّ", "2MS": "أَنْتَ", "2FS": "أَنْتِ",
            "2D": "أَنْتُمَا", "2MP": "أَنْتُمْ", "2FP": "أَنْتُنَّ", "1S": "أَنَا", "1P": "نَحْنُ"}
RELATIVES = {"MS": "الَّذِي", "FS": "الَّتِي", "MP": "الَّذِينَ", "FP": "اللَّاتِي", "MD": "اللَّذَانِ"}
# By gender and number, and whether the word is near (with هَا) or far (with the كَ of address).
DEMONSTRATIVES = {("MS", "near"): "هَٰذَا", ("MS", "far"): "ذَٰلِكَ", ("FS", "near"): "هَٰذِهِ", ("FS", "far"): "تِلْكَ",
                  ("P", "near"): "هَٰؤُلَاءِ", ("P", "far"): "أُولَٰئِكَ", ("MD", "near"): "هَٰذَانِ"}


def iter_pronoun_occurrences(segments: Iterable[Segment]) -> Iterator[ParticleOccurrence]:
    """Every independent pronoun, demonstrative and relative of the corpus, ayah by ayah."""
    for _ayah, grouped in groupby(segments, key=lambda segment: (segment.surah, segment.ayah)):
        ayah = tuple(grouped)
        words = {number: tuple(word) for number, word in groupby(ayah, key=lambda segment: segment.word)}
        for position, segment in enumerate(ayah):
            name = pronoun_name(segment, words[segment.word])
            if name:
                yield ParticleOccurrence(lemma=name, corpus_tag=corpus_tag(segment), surah=segment.surah,
                                         ayah=segment.ayah, word=segment.word, marker=marker_after(ayah[position + 1:]))


def pronoun_name(segment: Segment, word: Sequence[Segment]) -> str | None:
    """The citation form of a pronoun segment within its word; None when it is not one read here."""
    if segment.pos != NOUN or not segment.features:
        return None
    tag = segment.features[0]
    if tag == PRONOUN:
        return _personal(segment, word)
    if tag == DEMONSTRATIVE and lemma_of(segment) == _DEMONSTRATIVE_LEMMA:
        return _demonstrative(segment, word)
    if tag == RELATIVE and lemma_of(segment) == _RELATIVE_LEMMA:
        return RELATIVES.get(_agreement(segment), _RELATIVE_LEMMA)
    return None


def _personal(segment: Segment, word: Sequence[Segment]) -> str | None:
    lemma = lemma_of(segment)
    if lemma:                                  # إِيَّا, which carries its own lemma
        return lemma
    if _SUFFIX in segment.features or _after_preposition(segment, word):
        return None
    return PERSONAL.get(_agreement(segment))


def _demonstrative(segment: Segment, word: Sequence[Segment]) -> str:
    tags = {other.features[0] for other in word if other.pos == PARTICLE and other.features}
    distance = "far" if _ADDRESS in tags else "near" if _ATTENTION in tags else None
    return DEMONSTRATIVES.get((_agreement(segment), distance), _DEMONSTRATIVE_LEMMA)


def _after_preposition(segment: Segment, word: Sequence[Segment]) -> bool:
    return any(other.index < segment.index and other.pos == PARTICLE and other.features[:1] == (_PREPOSITION,)
               for other in word)


def _agreement(segment: Segment) -> str | None:
    """Person, gender and number as the corpus writes them: 3MS, MS, P…"""
    return next((feature for feature in segment.features[1:] if feature in PERSONAL or feature in _NUMBERS), None)

