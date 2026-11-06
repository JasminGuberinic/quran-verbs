"""Assemble the particle cards: everything a particle page shows, with its sound (and the pronoun
cards alike: the pronouns are another word list of the same engine, fil.stages.particles.PRONOUNS).

The composition root of the particle pages, like fil.stages.nuance_site for the nuances. The
particles (fil.particle_store) pass the corpus gate first (fil.particles.gate) — a count that is
not the corpus's, a cited ayah that does not hold the use, or a next word that does not show the
effect claimed stops the build. Then each particle gets:

  - its headword voiced by the checked synthetic voice (fil.speech) — one whose two readings
    disagree stops the build (`check_voiced`), never ships silent;
  - for a preposition, how the noun engine renders it in Bosnian (fil.nouns.bosnian.renderings)
    and a studied noun from its ayat whose page shows the cases (`caseNoun`);
  - each use's ayat as the other pages show them: the particle's word marked and recited on a
    tap (QuranHive), the ayah streamed, the free translation, and links to the verbs and nouns
    of that ayah that have pages of their own.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from fil.nouns.bosnian import renderings
from fil.particles import gate
from fil.particles.gate import ParticleConcordance
from fil.particles.model import Example, Particle, Text, Use
from fil.stages.nuance_site import ADJECTIVE, NOUN, VERB, StudiedCards, checked_voice
from fil.stages.particles import PARTICLES, WordList
from fil.stages.site import Sound
from fil.study import QuranWord

PAGE_LANGUAGES = ("bs", "en")
Location = tuple[int, int, int]


class ParticleGateFailed(ValueError):
    """A particle page says something about the Quran that the corpus does not bear out."""


class UnvoicedParticle(Exception):
    """A particle's headword would reach a learner without its checked voice."""


@dataclass(frozen=True)
class StudiedWords:
    """The words of the Quran that have a card of their own: each location to its card
    ({"kind": "verb" | "noun" | "adjective", "slug"})."""

    cards: Mapping[Location, dict]

    @classmethod
    def of(cls, verb_locations: Mapping[str, Iterable[Location]], lemma_locations: Mapping[str, Iterable[Location]],
           studied: StudiedCards) -> StudiedWords:
        """From where each verb ("root_form") and lemma ("lemma|root") stands, and our cards."""
        cards: dict[Location, dict] = {}
        for key, locations in verb_locations.items():
            if key in studied.verbs:
                cards.update(dict.fromkeys(locations, {"kind": VERB, "slug": studied.verbs[key]}))
        for key, locations in lemma_locations.items():
            card = _lemma_card(key, studied)
            if card:
                cards.update(dict.fromkeys(locations, card))
        return cls(cards)

    def in_ayah(self, surah: int, ayah: int, words: Sequence[QuranWord]) -> list[dict]:
        """The ayah's studied words, once per card, in reading order: {"text", "kind", "slug"}."""
        found: dict[str, dict] = {}
        for word in words:
            card = self.cards.get((surah, ayah, word.number))
            if card and card["slug"] not in found:
                found[card["slug"]] = {"text": word.text, **card}
        return list(found.values())


def _lemma_card(key: str, studied: StudiedCards) -> dict | None:
    if key in studied.nouns:
        return {"kind": NOUN, "slug": studied.nouns[key]}
    if key in studied.adjectives:
        return {"kind": ADJECTIVE, "slug": studied.adjectives[key]}
    return None


def assemble_particles(sound: Sound, ayat: Mapping[tuple[int, int], tuple[QuranWord, ...]], studied: StudiedWords,
                       words: WordList = PARTICLES, concordance: ParticleConcordance | None = None) -> tuple[dict, ...]:
    """Every card of the word list (the particles, the pronouns), gated; none when none is written yet."""
    particles = words.load()
    if not particles:
        return ()
    if concordance is None:
        concordance = words.concordance()   # reads the corpus: only when there are words to check
    problems = gate.problems(particles, concordance)
    if problems:
        raise ParticleGateFailed(f"{len(problems)} {words.name} claims the corpus does not bear out "
                                 f"(`fil {words.name} check`): {problems[:5]}")
    cards = tuple(ParticleCardBuilder(particle, concordance, sound, ayat, studied).card() for particle in particles)
    print(f"  {words.name}: {' · '.join(card['arabic'] for card in cards)}", flush=True)
    return cards


class ParticleCardBuilder:
    """One particle's card; holds what its parts share (the corpus, the sound, our cards)."""

    def __init__(self, particle: Particle, concordance: ParticleConcordance, sound: Sound,
                 ayat: Mapping[tuple[int, int], tuple[QuranWord, ...]], studied: StudiedWords) -> None:
        self.particle, self.concordance, self.sound, self.ayat, self.studied = particle, concordance, sound, ayat, studied

    def card(self) -> dict:
        particle = self.particle
        counts = gate.use_counts(particle, self.concordance)
        uses = [self._use(use, counts[use.key]) for use in particle.uses]
        audio = checked_voice(self.sound, particle.said)
        return {"slug": particle.slug, "arabic": particle.arabic, "audio": audio, "count": particle.count,
                "meaning": _texts(particle.meaning), "grammar": _texts(particle.grammar), "kinds": list(particle.kinds),
                "preposition": self._preposition(), "caseNoun": _case_noun(uses) if particle.preposition else None,
                "uses": uses, "sources": list(particle.sources), "unvoiced": [] if audio else [particle.said]}

    def _preposition(self) -> list[dict] | None:
        """How a Bosnian gloss renders it: [{"word": "u", "case": "L"}, …]."""
        name = self.particle.preposition
        return [{"word": word, "case": case} for word, case in renderings(name)] if name else None

    def _use(self, use: Use, count: int | None) -> dict:
        return {"key": use.key, "kind": use.kind, "title": _texts(use.title), "explanation": _texts(use.explanation),
                "effect": use.effect, "count": count, "ayat": [self._ayah(use, example) for example in use.ayat]}

    def _ayah(self, use: Use, example: Example) -> dict:
        surah, number = example.surah, example.ayah
        marked = gate.marked_occurrence(self.particle, use, example, self.concordance).word
        quran_words = self.ayat[(surah, number)]
        words = [{"text": word.text, "hit": word.number == marked,
                  **({"audio": self.sound.word(surah, number, word.number)} if word.number == marked else {})}
                 for word in quran_words]
        return {"ref": example.reference, "audio": self.sound.ayah(surah, number), "why": _texts(example.why),
                "translation": {language: text for language, text in self.sound.translations.of(surah, number).items()
                                if language in PAGE_LANGUAGES},
                "words": words, "studied": self.studied.in_ayah(surah, number, quran_words)}


def _case_noun(uses: Sequence[dict]) -> dict | None:
    """The first studied noun of the particle's ayat: its page explains the cases on itself."""
    return next((word for use in uses for ayah in use["ayat"] for word in ayah["studied"] if word["kind"] == NOUN),
                None)


def _texts(text: Text) -> dict[str, str]:
    return {"bs": text.bs, "en": text.en}


# ---------------------------------------------------------------- the voice gate

def check_voiced(cards: Iterable[dict], documented: Mapping[str, str]) -> None:
    """Fail the build when a headword ships silent without a documented reason (data/noun_unvoiced.json)."""
    silent = sorted({f"{card['slug']}: {text}" for card in cards for text in card["unvoiced"] if text not in documented})
    if silent:
        raise UnvoicedParticle(f"{len(silent)} particle headwords have no checked voice (fix fil.speech, or document "
                               f"them in data/noun_unvoiced.json): {silent}")
