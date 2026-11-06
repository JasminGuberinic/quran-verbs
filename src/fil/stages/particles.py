"""The Quran's particles (docs/PARTICLES-PLAN.md): measure them, check the pages' claims, export for review.

    fil particles frequency          every particle lemma and tag of the corpus by count — what to write next
    fil particles find LEMMA TAG [N] short ayat that hold LEMMA as TAG ("NEG|FAM:إِنّ"), with the word
                                     numbers and what the next word shows — candidates for a use's ayat
    fil particles check              run the corpus gate over data/particles.json (counts, cited ayat,
                                     effects); prints only problems and a one-line summary, exits 1 on any
    fil particles review-export      build/particles/blind.json: every claim with its cited ayat (Arabic,
                                     the marked word, Pickthall's English), English and Bosnian, for a
                                     blind reviewer — no notes, no reasons

This stage is the composition root of the particle engine: it reads the corpus
(fil.corpus.particles) and wires it in as the gate's ParticleConcordance.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence

from fil import particle_store
from fil.corpus.parse import iter_segments
from fil.corpus.particles import iter_particle_occurrences
from fil.particles import gate
from fil.particles.model import CorpusTag, Particle, ParticleOccurrence, Text
from fil.resources import BUILD_DIR, QAC_MORPHOLOGY

OUT = BUILD_DIR / "particles"
CANDIDATES_SHOWN = 25
SHORT_AYAH = 10          # words: `find` lists ayat up to this long first


class CorpusParticleConcordance:
    """The gate's ParticleConcordance over the corpus: occurrences by (lemma, tag)."""

    def __init__(self, occurrences: Iterable[ParticleOccurrence]) -> None:
        self._by_key: dict[tuple[str, CorpusTag], list[ParticleOccurrence]] = defaultdict(list)
        for occurrence in occurrences:
            self._by_key[(occurrence.lemma, occurrence.corpus_tag)].append(occurrence)

    @classmethod
    def from_corpus(cls) -> CorpusParticleConcordance:
        with QAC_MORPHOLOGY.open(encoding="utf-8") as lines:
            return cls(iter_particle_occurrences(iter_segments(lines)))

    def occurrences(self, lemma: str, tag: CorpusTag) -> Sequence[ParticleOccurrence]:
        return self._by_key.get((lemma, tag), ())

    def counts(self) -> Counter:
        return Counter({key: len(found) for key, found in self._by_key.items()})


# ---------------------------------------------------------------- commands

def frequency() -> None:
    for (lemma, tag), count in CorpusParticleConcordance.from_corpus().counts().most_common():
        print(f"{count:6}  {lemma}\t{tag}")


def find(lemma: str, tag: str, shown: int = CANDIDATES_SHOWN) -> None:
    """The shortest ayat holding the particle under the tag: «the word», its number, the next word's marker."""
    from fil.stages.site import read_corpus

    ayat = read_corpus().ayat
    found = CorpusParticleConcordance.from_corpus().occurrences(lemma, CorpusTag.parse(tag))
    markers = Counter(occurrence.marker for occurrence in found)
    print(f"{lemma} {tag}: {len(found)} — next word shows {dict(markers.most_common())}")
    for occurrence in sorted(found, key=lambda occurrence: len(ayat[(occurrence.surah, occurrence.ayah)]))[:shown]:
        words = ayat[(occurrence.surah, occurrence.ayah)]
        text = " ".join(f"«{word.text}»" if word.number == occurrence.word else word.text for word in words)
        print(f"  {occurrence.surah}:{occurrence.ayah}:{occurrence.word} [{occurrence.marker}] {text}")


def check() -> list[str]:
    """The gate over the stored particles; the problems found (printed), none when they may ship."""
    particles = particle_store.load_particles()
    found = gate.problems(particles, CorpusParticleConcordance.from_corpus())
    print("\n".join(found) if found else "", end="\n" if found else "")
    uses = sum(len(particle.uses) for particle in particles)
    ayat = sum(len(use.ayat) for particle in particles for use in particle.uses)
    print(f"particles: {len(particles)} particles, {uses} uses, {ayat} cited ayat — {len(found)} problems")
    return found


def review_export(slugs: Sequence[str] = ()) -> None:
    """The claims a blind reviewer checks against the ayat — what we say, never why we decided it."""
    from fil.ayah_translations import AyahTranslations
    from fil.stages.site import read_corpus

    particles = [particle for particle in particle_store.load_particles() if not slugs or particle.slug in slugs]
    concordance = CorpusParticleConcordance.from_corpus()
    ayat, translations = read_corpus().ayat, AyahTranslations()
    claims = [claim for particle in particles for claim in _claims(particle, concordance, ayat, translations)]
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "blind.json"
    target.write_text(json.dumps(claims, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"particles: {len(claims)} claims → {target}")


def _claims(particle: Particle, concordance, ayat: Mapping, translations) -> list[dict]:
    def ayah(use, example) -> dict:
        occurrence = gate.marked_occurrence(particle, use, example, concordance)
        words = ayat[(example.surah, example.ayah)]
        return {"ref": example.reference, "arabic": " ".join(word.text for word in words),
                "markedWord": next(word.text for word in words if word.number == occurrence.word),
                "english": translations.of(example.surah, example.ayah).get("en", {}).get("text", ""),
                "why": _both(example.why)}

    head = {"id": f"{particle.slug}:particle", "particle": particle.arabic, "sources": list(particle.sources),
            "meaning": _both(particle.meaning), "grammar": _both(particle.grammar)}
    return [head, *({"id": f"{particle.slug}:{use.key}", "particle": particle.arabic, "kind": use.kind,
                     "corpusTags": [str(tag) for tag in use.tags], "nextWordShows": use.effect,
                     "title": _both(use.title), "explanation": _both(use.explanation),
                     "ayat": [ayah(use, example) for example in use.ayat]}
                    for use in particle.uses)]


def _both(text: Text) -> dict[str, str]:
    return {"en": text.en, "bs": text.bs}


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[2:]
    if args == ["frequency"]:
        frequency()
        return
    if args[:1] == ["find"] and len(args) in (3, 4):
        find(args[1], args[2], int(args[3]) if len(args) == 4 else CANDIDATES_SHOWN)
        return
    if args == ["check"]:
        if check():
            raise SystemExit(1)
        return
    if args[:1] == ["review-export"]:
        review_export(args[1:])
        return
    print(__doc__)
    raise SystemExit(2)
