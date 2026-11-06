"""The corpus gate of the particle pages: what a page says about the Quran must be so.

  - every tag a use names is one the corpus files the particle under;
  - the particle's stated count is the corpus's count over the tags its uses cover;
  - every cited ayah holds the particle under one of the use's tags — at the pinned word, or
    once, so the page marks the right word (an ayah that holds the use twice must pin it);
  - where a use says what the next word shows (لَمْ → jussive), the marked word's next
    inflected word shows exactly that.

The corpus is behind a port (`ParticleConcordance`), so the rules are tested without it and
the stage wires in the corpus reader (fil.stages.particles).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Protocol

from fil.particles.model import CorpusTag, Example, Particle, ParticleOccurrence, Use


class ParticleConcordance(Protocol):
    def occurrences(self, lemma: str, tag: CorpusTag) -> Sequence[ParticleOccurrence]:
        """Every place the corpus files this lemma under this tag; empty when it never does."""
        ...


class ExampleNotFound(LookupError):
    """A cited ayah does not hold the use where the page would mark it."""


def problems(particles: Iterable[Particle], concordance: ParticleConcordance) -> list[str]:
    """Everything a particle page claims about the corpus that is not so; empty when they may ship."""
    return [problem for particle in particles for problem in _particle_problems(particle, concordance)]


def marked_occurrence(particle: Particle, use: Use, example: Example,
                      concordance: ParticleConcordance) -> ParticleOccurrence:
    """The one word of the cited ayah that shows the use: the pinned word, else the only one."""
    candidates = [occurrence for occurrence in _occurrences_in(particle, use, example, concordance)
                  if example.word is None or occurrence.word == example.word]
    words = sorted({occurrence.word for occurrence in candidates})
    where = f"{example.reference}{f':{example.word}' if example.word else ''}"
    if not words:
        raise ExampleNotFound(f"{where} does not hold {particle.arabic} as {_tags(use)}")
    if len(words) > 1:
        raise ExampleNotFound(f"{where} holds {particle.arabic} as {_tags(use)} at words {words}: pin one (s:a:w)")
    return candidates[0]


def use_counts(particle: Particle, concordance: ParticleConcordance) -> Mapping[str, int | None]:
    """How often each use occurs — None for a use whose tags another use shares (the corpus
    files فِي of place and of cause alike, so it cannot count them apart)."""
    shared = {tag for use in particle.uses for tag in use.tags
              if sum(tag in other.tags for other in particle.uses) > 1}
    return {use.key: None if shared & set(use.tags) else _count(particle.lemma, use.tags, concordance)
            for use in particle.uses}


def _particle_problems(particle: Particle, concordance: ParticleConcordance) -> list[str]:
    found = [f"{particle.slug}: the corpus never files {particle.lemma} as {tag}"
             for tag in particle.corpus_tags if not concordance.occurrences(particle.lemma, tag)]
    counted = _count(particle.lemma, particle.corpus_tags, concordance)
    if counted != particle.count:
        found.append(f"{particle.slug}: the corpus counts {counted}, the data says {particle.count}")
    return found + [problem for use in particle.uses for example in use.ayat
                    for problem in _example_problems(particle, use, example, concordance)]


def _example_problems(particle: Particle, use: Use, example: Example, concordance: ParticleConcordance) -> list[str]:
    where = f"{particle.slug} {use.key}"
    try:
        occurrence = marked_occurrence(particle, use, example, concordance)
    except ExampleNotFound as missing:
        return [f"{where}: {missing}"]
    if use.effect and occurrence.marker != use.effect:
        return [f"{where}: at {example.reference}:{occurrence.word} the next word shows {occurrence.marker}, "
                f"not {use.effect}"]
    return []


def _occurrences_in(particle: Particle, use: Use, example: Example,
                    concordance: ParticleConcordance) -> list[ParticleOccurrence]:
    return [occurrence for tag in use.tags for occurrence in concordance.occurrences(particle.lemma, tag)
            if (occurrence.surah, occurrence.ayah) == (example.surah, example.ayah)]


def _count(lemma: str, tags: Iterable[CorpusTag], concordance: ParticleConcordance) -> int:
    return sum(len(concordance.occurrences(lemma, tag)) for tag in tags)


def _tags(use: Use) -> str:
    return " or ".join(str(tag) for tag in use.tags)
