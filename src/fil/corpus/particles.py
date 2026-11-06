"""Read every particle of the Quran out of the corpus, with what the word after it shows.

The corpus tags a particle by what it does, not only by what it is (corpus.quran.com tagset):

    2:6:1:1    إِنَّ     P   ACC|LEM:إِنّ|FAM:إِنّ        an "accusative particle", of inna's family
    2:6:8:1    لَمْ     P   NEG|LEM:لَم                  a negative particle
    2:3:6:1    وَ       P   REM|PREF|LEM:و              wa as a proclitic, here "resumption"
    2:3:6:3    مَّا     N   REL|LEM:ما                   mā as a relative — the corpus files it as a noun

so one lemma (و, ما, ل) appears under several tags, one per use. A particle is known here by
its lemma, its tag and — where the corpus gives one — its family (لا of absolute negation is
NEG|FAM:إِنّ, mā that works like laysa is NEG|FAM:كَان): `CorpusTag`.

Every occurrence also records what the next inflected word shows — its case (NOM, ACC, GEN)
or its mood (IND, SUBJ, JUS) — so the gate can hold "لَمْ makes the verb jussive" to the very
ayat cited for it. The next word is the first noun or verb segment after the particle within
the ayah, the article skipped (فِي ٱلْأَرْضِ); when a suffixed pronoun (بِهِ) or another particle
(إِنَّ فِي) comes first, the governed word shows nothing, and `marker` is None.

Function words the corpus files as rootless nouns (relative mā, إِذَا, the interrogative
hamza) are read too: a learner meets them among the particles. Pure: segments in.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from itertools import groupby

from fil.corpus.parse import Segment
from fil.particles.model import CorpusTag, ParticleOccurrence

PARTICLE, NOUN, VERB = "P", "N", "V"
ARTICLE = "DET"
CASE_MARKERS = ("NOM", "ACC", "GEN")
MOOD_MARKERS = ("IND", "SUBJ", "JUS")
_LEMMA, _FAMILY, _MOOD, _ROOT = "LEM:", "FAM:", "MOOD:", "ROOT:"
_SUFFIX, _PRONOUN = "SUFF", "PRON"
# Rootless nouns that are function words a learner meets among the particles.
_FUNCTION_NOUN_TAGS = frozenset({"REL", "INTG", "COND", "T"})


def iter_particle_occurrences(segments: Iterable[Segment]) -> Iterator[ParticleOccurrence]:
    """Every particle (and function-word noun) of the corpus, ayah by ayah."""
    for _ayah, grouped in groupby(segments, key=lambda segment: (segment.surah, segment.ayah)):
        ayah = tuple(grouped)
        yield from (_occurrence(segment, ayah[position + 1:]) for position, segment in enumerate(ayah)
                    if is_particle(segment))


def is_particle(segment: Segment) -> bool:
    if _lemma(segment) is None:
        return False
    if segment.pos == PARTICLE:
        return segment.features[0] != ARTICLE
    rootless = not any(feature.startswith(_ROOT) for feature in segment.features)
    return segment.pos == NOUN and rootless and segment.features[0] in _FUNCTION_NOUN_TAGS


def _occurrence(segment: Segment, following: Sequence[Segment]) -> ParticleOccurrence:
    return ParticleOccurrence(lemma=_lemma(segment), corpus_tag=_corpus_tag(segment), surah=segment.surah,
                              ayah=segment.ayah, word=segment.word, marker=marker_after(following))


def marker_after(following: Sequence[Segment]) -> str | None:
    """The case or mood of the word a particle stands before; None when nothing shows one."""
    for segment in following:
        if segment.pos == PARTICLE and segment.features[0] == ARTICLE:
            continue
        if segment.pos not in (NOUN, VERB) or _is_pronoun_suffix(segment):
            return None
        return _marker(segment)
    return None


def _marker(segment: Segment) -> str | None:
    case = next((feature for feature in segment.features if feature in CASE_MARKERS), None)
    mood = next((feature.removeprefix(_MOOD) for feature in segment.features if feature.startswith(_MOOD)), None)
    return case or mood


def _is_pronoun_suffix(segment: Segment) -> bool:
    return _PRONOUN in segment.features and _SUFFIX in segment.features


def _corpus_tag(segment: Segment) -> CorpusTag:
    family = next((feature.removeprefix(_FAMILY) for feature in segment.features if feature.startswith(_FAMILY)), None)
    return CorpusTag(segment.features[0], family)


def _lemma(segment: Segment) -> str | None:
    return next((feature.removeprefix(_LEMMA) for feature in segment.features if feature.startswith(_LEMMA)), None)
