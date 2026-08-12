"""The words the Quran itself uses — the vetted vocabulary a sentence is built from.

The sentence gate can only ever REJECT a bad draft. The cheaper win is to stop drafting
bad sentences: if every word already comes from the Quran, the building blocks are real
words with real spellings by construction, and there is nothing left for the analyzer to
discover. It also happens to be the pedagogically right answer — a learner practising
Quranic verbs should meet Quranic vocabulary around them, not arbitrary modern nouns.

We already own the data. The corpus annotates EVERY segment, not just verbs, so the
noun/adjective vocabulary of the Quran falls straight out of the same file the verb
catalogue is built from: lemma, root, how often it occurs, and the spellings in which
it actually appears.

Verbs are deliberately absent — they are the subject being taught and have their own
catalogue. Function words are absent too, and the corpus separates them for us in a way
worth knowing: it tags pronouns, relatives and conditionals as nouns as well, but only a
genuine lexical word carries a ROOT. هُوَ, إِذا and مَن have none; يَوْم and رَبّ do. So
"has a root" is the rule that keeps the bank to words a sentence can be built out of —
and it is the same triliteral root the rest of this engine is organised around.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable

from fil.corpus.parse import Segment

_NOUN = "N"  # the corpus tags nouns, adjectives, participles and names alike


@dataclass(frozen=True)
class VocabularyEntry:
    """One Quranic word, aggregated over every place it occurs.

    No ayah references: this is a word bank for composing sentences, not a concordance
    (the ayāt that matter — the ones for the verb being taught — live on the verb).
    """

    lemma: str                    # dictionary form as the corpus lemmatises it
    root: str                     # every entry has one — that is what makes it vocabulary
    word_class: str               # "noun" | "adjective" | "proper_noun"
    occurrence_count: int
    surfaces: tuple[str, ...]     # spellings actually attested, most frequent first


def build_vocabulary(segments: Iterable[Segment]) -> list[VocabularyEntry]:
    """Aggregate the corpus's noun segments into a word bank, most frequent first."""
    grouped: dict[tuple[str, str], list[Segment]] = defaultdict(list)
    for segment in segments:
        word_class = _word_class(segment)
        if word_class is None:
            continue
        grouped[(_lemma(segment), word_class)].append(segment)

    entries = [_entry(lemma, word_class, found) for (lemma, word_class), found in grouped.items()]
    return sorted(entries, key=lambda entry: (-entry.occurrence_count, entry.lemma))


def _entry(lemma: str, word_class: str, segments: list[Segment]) -> VocabularyEntry:
    surfaces = Counter(segment.surface for segment in segments)
    return VocabularyEntry(
        lemma=lemma,
        root=_root(segments[0]),
        word_class=word_class,
        occurrence_count=len(segments),
        surfaces=tuple(surface for surface, _count in surfaces.most_common()),
    )


def _word_class(segment: Segment) -> str | None:
    """Our class for a segment, or None if it is not vocabulary we teach.

    The root test is what excludes function words: the corpus files pronouns, relatives
    and conditionals under the same tag as nouns, but leaves them rootless.
    """
    if segment.pos != _NOUN or _is_clitic(segment) or not _feature(segment, "ROOT"):
        return None
    if "PN" in segment.features:
        return "proper_noun"
    if "ADJ" in segment.features:
        return "adjective"
    return "noun"


def _root(segment: Segment) -> str:
    """The segment's root — always present here, since rootless words are not vocabulary."""
    root = _feature(segment, "ROOT")
    if root is None:
        raise ValueError(f"vocabulary segment without a root: {segment}")
    return root


def _is_clitic(segment: Segment) -> bool:
    """Prefixes and suffixes attach to a word; they are not words themselves."""
    return "PREF" in segment.features or "SUFF" in segment.features


def _lemma(segment: Segment) -> str:
    """The corpus lemma, falling back to the surface when a segment carries none."""
    return _feature(segment, "LEM") or segment.surface


def _feature(segment: Segment, key: str) -> str | None:
    prefix = f"{key}:"
    return next(
        (feature[len(prefix) :] for feature in segment.features if feature.startswith(prefix)),
        None,
    )
