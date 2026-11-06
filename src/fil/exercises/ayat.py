"""The exercises read in an ayah: Nijanse / Nuances and Čestica / Particles.

Nuances: an ayah a near-synonym group cites for one of its words, that word blanked — which of the
group's words does the Quran say here? The other words of the group are the distractors: the
question is what the Quran says, a fact the corpus places (the nuance gate holds every cited ayah
to the member's word), so they are wrong however close their meanings. An ayah the group cites for
two of its words is never asked. After answering: the word as the Quran says it, recited, and the
group's note on why it fits there.

Particles: an ayah a particle page cites for one of its uses, the particle marked — what does it do
to the word after it? The answers are the three cases (for a particle before a noun) or the three
moods (before a verb); the right one is the use's effect, which the particle gate holds to the
corpus's reading of the next word in every cited ayah.

An ayah whose note names another canonical reading (qirāʾa) is asked in neither kind: what is right
in Ḥafṣ's reading may be wrong in another's.

Pure.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from fil.exercises.model import NUANCE, PARTICLE, Bilingual, Exercise, Option, QuranTranslation, Segment
from fil.exercises.text import same_spelling, stable_order

OPTION_COUNT = 4
NOUN_EFFECTS = ("NOM", "ACC", "GEN")
MOOD_EFFECTS = ("IND", "SUBJ", "JUS")


@dataclass(frozen=True)
class AyahWord:
    text: str
    is_hit: bool = False
    sound: str | None = None      # the word's own recitation


@dataclass(frozen=True)
class CitedAyah:
    reference: str                # "70:19"
    words: tuple[AyahWord, ...]
    why: Bilingual                # why the word fits here / what the particle does here
    translation: QuranTranslation | None = None
    # The note says another canonical reading has it otherwise (80:4: Ḥafṣ's subjunctive, others the
    # indicative): a question with a different right answer in another reading is never asked.
    has_other_reading: bool = False


@dataclass(frozen=True)
class NuanceMember:
    arabic: str
    meaning: Bilingual
    ayat: tuple[CitedAyah, ...]


@dataclass(frozen=True)
class NuanceGroup:
    word: str                     # "nuance:insan-bashar"
    members: tuple[NuanceMember, ...]


@dataclass(frozen=True)
class ParticleUse:
    word: str                     # "particle:lam"
    particle: str                 # the particle as its page writes it: لَمْ, لِـ
    key: str                      # the use's key on the particle page
    title: Bilingual
    effect: str | None
    ayat: tuple[CitedAyah, ...]


# ---------------------------------------------------------------- nuances

def nuance_exercises(groups: Sequence[NuanceGroup]) -> list[Exercise]:
    return [exercise for group in groups for exercise in _of_group(group)]


def _of_group(group: NuanceGroup) -> list[Exercise]:
    cited = _citations(group)
    return [_nuance_exercise(group, position, ayah)
            for position, member in enumerate(group.members) if _is_distinct(member, group.members)
            for ayah in member.ayat if cited[ayah.reference] == 1 and _is_askable(ayah)]


def _citations(group: NuanceGroup) -> Counter[str]:
    """How many of the group's words cite each ayah (a word citing it twice counts once)."""
    return Counter(reference for member in group.members for reference in {ayah.reference for ayah in member.ayat})


def _is_askable(ayah: CitedAyah) -> bool:
    return any(word.is_hit for word in ayah.words) and not ayah.has_other_reading


def _is_distinct(member: NuanceMember, members: Sequence[NuanceMember]) -> bool:
    """No other word of the group is written like this one."""
    return not any(other is not member and same_spelling(other.arabic, member.arabic) for other in members)


def _nuance_exercise(group: NuanceGroup, position: int, ayah: CitedAyah) -> Exercise:
    member = group.members[position]
    others = stable_order((other for other in group.members if other is not member), lambda other: other.arabic,
                          salt=f"{group.word}|{ayah.reference}")
    options = (Option(True, arabic=member.arabic),
               *(Option(False, arabic=other.arabic) for other in others[:OPTION_COUNT - 1]))
    hits = [word for word in ayah.words if word.is_hit]
    slug = group.word.split(":", 1)[1]
    return Exercise(kind=NUANCE, key=f"{slug}-{position + 1}-{ayah.reference.replace(':', '-')}", words=(group.word,),
                    options=options, passage=tuple(Segment(word.text, is_blank=word.is_hit) for word in ayah.words),
                    reference=ayah.reference, quran_translation=ayah.translation, explanation=ayah.why,
                    answer_word=" … ".join(word.text for word in hits),
                    answer_sound=next((word.sound for word in hits if word.sound), None), gloss=member.meaning)


# ---------------------------------------------------------------- particles

def particle_exercises(uses: Sequence[ParticleUse]) -> list[Exercise]:
    return [_particle_exercise(use, ayah) for use in uses if _effects_of(use.effect) for ayah in use.ayat
            if sum(1 for word in ayah.words if word.is_hit) == 1 and not ayah.has_other_reading]


def _effects_of(effect: str | None) -> tuple[str, ...]:
    """The answers a use is asked among: the cases before a noun, the moods before a verb."""
    if effect in NOUN_EFFECTS:
        return NOUN_EFFECTS
    if effect in MOOD_EFFECTS:
        return MOOD_EFFECTS
    return ()


def _particle_exercise(use: ParticleUse, ayah: CitedAyah) -> Exercise:
    slug = use.word.split(":", 1)[1]
    hit = next(word for word in ayah.words if word.is_hit)
    return Exercise(kind=PARTICLE, key=f"{slug}-{use.key}-{ayah.reference.replace(':', '-')}", words=(use.word,),
                    options=tuple(Option(effect == use.effect, code=effect) for effect in _effects_of(use.effect)),
                    passage=tuple(Segment(word.text, is_marked=word.is_hit) for word in ayah.words),
                    lead=use.particle, reference=ayah.reference, quran_translation=ayah.translation,
                    explanation=ayah.why, answer_word=hit.text, answer_sound=hit.sound, gloss=use.title,
                    facts={"effect": use.effect or ""})
