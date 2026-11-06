"""Which part of a whole word a learner looks it up under: its headword.

The corpus takes a word apart into proclitics, a stem and suffixes, and a word may hold several
things a learner could look up — وَلَمْ is "and" + "not", فَقَالُوا is "so" + "they said", لَهُ is
"for" + "him". A token is counted once, under the most lexical of its parts:

    rank 0   a verb (قَالُوا), or a function word the corpus files as a verb or a rooted noun
             (لَيْسَ, كَيْفَ, كَمْ — the particle pages teach them as particles)
    rank 1   a rooted noun or adjective (أَحَد, رَحْمٰن), its article and case aside
    rank 2   an independent pronoun, demonstrative or relative, named as fil.corpus.pronouns names it
    rank 3   a particle standing as the word's stem (لَمْ in وَلَمْ, فِي in فِيهِ)
    rank 4   a proclitic particle, when nothing else heads the word (لِـ in لَهُ, بِـ in بِهِ)

and, should a word hold none of these, its first stem as it is (`OTHER`). So a suffixed pronoun
(the ـهُ of لَهُ) never heads a word, and the و of وَلَمْ is not counted where لَمْ is.

Pure: a word's segments in, a Headword out. `verb_key` lets the caller pass the verb the
corrected catalogue files the word under (data/corpus_corrections.json), which can differ from
the corpus's own tag.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from itertools import groupby

from fil.corpus.parse import Segment
from fil.corpus.particles import NAMED_FUNCTION_WORDS, corpus_tag, is_particle, lemma_of
from fil.corpus.pronouns import pronoun_name
from fil.surahs.model import NOUN, OTHER, PARTICLE, PRONOUN, VERB, Headword, Location, Token

_VERB, _NOUN = "V", "N"
_PREFIX, _SUFFIX = "PREF", "SUFF"
_ROOT, _VERB_FORM = "ROOT:", "VF:"


class UnreadableWord(ValueError):
    """A word the corpus gives no segment for."""


def headword_of(word: Sequence[Segment], verb_key: str | None = None) -> Headword:
    """The headword of one whole word (its segments in order)."""
    if not word:
        raise UnreadableWord("a word needs at least one segment")
    ranked = [(rank, position, headword) for position, segment in enumerate(word)
              for rank, headword in [_classified(segment, word, verb_key)] if headword is not None]
    if ranked:
        return min(ranked, key=lambda found: found[:2])[2]
    return _as_written(word)


def _classified(segment: Segment, word: Sequence[Segment], verb_key: str | None) -> tuple[int, Headword | None]:
    lemma = lemma_of(segment)
    if lemma in NAMED_FUNCTION_WORDS:
        return 0, _particle(segment, lemma)
    if segment.pos == _VERB:
        return 0, Headword(VERB, verb_key or _verb_key(segment), lemma or segment.surface)
    if _is_stem(segment) and segment.pos == _NOUN and _root(segment):
        return 1, Headword(NOUN, f"{lemma or segment.surface}|{_root(segment)}", lemma or segment.surface)
    name = pronoun_name(segment, word)
    if name:
        return 2, Headword(PRONOUN, f"{name}|{corpus_tag(segment)}", name)
    if is_particle(segment):
        return (3 if _is_stem(segment) else 4), _particle(segment, lemma)
    return 9, None


def _particle(segment: Segment, lemma: str) -> Headword:
    return Headword(PARTICLE, f"{lemma}|{corpus_tag(segment)}", lemma)


def _as_written(word: Sequence[Segment]) -> Headword:
    """A word none of whose parts is a word we could look up: shown as its first stem."""
    stem = next((segment for segment in word if _is_stem(segment)), word[0])
    shown = lemma_of(stem) or stem.surface
    return Headword(OTHER, f"{stem.pos}:{shown}", shown)


def _is_stem(segment: Segment) -> bool:
    return _PREFIX not in segment.features and _SUFFIX not in segment.features


def _root(segment: Segment) -> str | None:
    return next((feature.removeprefix(_ROOT) for feature in segment.features if feature.startswith(_ROOT)), None)


def _verb_key(segment: Segment) -> str:
    """"قول_1", as the catalogue keys a verb (root, form)."""
    form = next((feature.removeprefix(_VERB_FORM) for feature in segment.features if feature.startswith(_VERB_FORM)), "1")
    return f"{_root(segment)}_{form}"


def tokens_of(segments: Iterable[Segment], verb_keys: Mapping[Location, str]) -> tuple[Token, ...]:
    """Every whole word of the segments (in corpus order) as a token with its headword; `verb_keys`
    holds the corrected catalogue's verb at each place it files one."""
    return tuple(
        Token(surah, ayah, number, "".join(segment.surface for segment in word),
              headword_of(word, verb_keys.get((surah, ayah, number))))
        for (surah, ayah, number), grouped in groupby(segments, key=lambda segment: (segment.surah, segment.ayah, segment.word))
        for word in [tuple(grouped)]
    )
