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
hamza) are read too: a learner meets them among the particles. So are three it files elsewhere,
named by lemma, each under its own part of speech where the corpus gives no tag of use:

    2:28:1:1   كَيْفَ    N   INTG|ROOT:كيف|LEM:كَيْف       a rooted noun ("how?"), INTG
    2:259:52:1 كَيْفَ    N   ROOT:كيف|LEM:كَيْف            the same with no tag of use: N
    6:6:3:1    كَمْ     N   LEM:كَم|ACC                    "how many a…" with no tag of use: N
    2:177:1:1  لَّيْسَ   V   PERF|…|LEM:لَيْسَ|FAM:كَان     a verb of كَانَ's family: V|FAM:كَان

Pure: segments in.
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
# Function words the corpus files as a rooted noun or a verb; the learner meets them among the particles.
NAMED_FUNCTION_WORDS = frozenset({"كَيْف", "كَم", "لَيْسَ"})


def iter_particle_occurrences(segments: Iterable[Segment]) -> Iterator[ParticleOccurrence]:
    """Every particle (and function-word noun) of the corpus, ayah by ayah."""
    for _ayah, grouped in groupby(segments, key=lambda segment: (segment.surah, segment.ayah)):
        ayah = tuple(grouped)
        yield from (_occurrence(segment, ayah[position + 1:]) for position, segment in enumerate(ayah)
                    if is_particle(segment))


def is_particle(segment: Segment) -> bool:
    lemma = lemma_of(segment)
    if lemma is None:
        return False
    if lemma in NAMED_FUNCTION_WORDS:
        return True
    if segment.pos == PARTICLE:
        return segment.features[0] != ARTICLE
    rootless = not any(feature.startswith(_ROOT) for feature in segment.features)
    return segment.pos == NOUN and rootless and segment.features[0] in _FUNCTION_NOUN_TAGS


def _occurrence(segment: Segment, following: Sequence[Segment]) -> ParticleOccurrence:
    return ParticleOccurrence(lemma=lemma_of(segment), corpus_tag=corpus_tag(segment), surah=segment.surah,
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


def corpus_tag(segment: Segment) -> CorpusTag:
    """The tag of what the word does, with its family; a verb (لَيْسَ) or a noun the corpus gives no
    tag of use (كَمْ of quantity) is filed under its part of speech."""
    family = next((feature.removeprefix(_FAMILY) for feature in segment.features if feature.startswith(_FAMILY)), None)
    first = segment.features[0]
    has_no_tag_of_use = segment.pos == VERB or first.startswith((_ROOT, _LEMMA))
    return CorpusTag(segment.pos if has_no_tag_of_use else first, family)


def lemma_of(segment: Segment) -> str | None:
    return next((feature.removeprefix(_LEMMA) for feature in segment.features if feature.startswith(_LEMMA)), None)
