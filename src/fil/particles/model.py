"""What a particle page holds, read from data/particles.json and validated.

Pure data. A particle (فِي, لَمْ, مَا…) is one corpus lemma; each of its uses is filed by the
corpus under its own tag (مَا negating is NEG, relative is REL, asking is INTG), so a use names
the tags it covers, says what it does in plain words, what the next word shows because of it
(the genitive after a preposition, the jussive after لَمْ) and cites 1–3 ayat. A preposition
names how the noun engine renders it in Bosnian (fil.nouns.bosnian), so the page and the noun
cards say the same. Every learner-facing text is written in Bosnian and English; nothing that
fails these rules is ever built (InvalidParticleData names what is wrong).
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from fil.nouns.bosnian import ARABIC_PREPOSITIONS

LANGUAGES = ("bs", "en")
MIN_AYAT, MAX_AYAT = 1, 3
TATWEEL = "ـ"     # how a proclitic is written alone: بِـ
# What a use is, in the terms of Arabic grammar; the page names each in the reader's language.
KINDS = ("preposition", "conjunction", "resumption", "circumstantial", "oath", "result", "cause",
         "negation", "prohibition", "absoluteNegation", "innaFamily", "preventive", "conditional",
         "subordinator", "interpretive", "interrogative", "relative", "restriction", "exception",
         "certainty", "purpose", "command", "timeAdverb", "surprise", "emphasis", "equalization", "vocative",
         "retraction", "amendment", "inceptive", "future", "exhortation", "detail", "attention", "aversion",
         "answer", "accompaniment", "defectiveVerb", "quantity", "alternative", "personalPronoun", "objectPronoun",
         "demonstrative")
# What the next word shows because of the particle: a case or a mood, as the corpus tags them.
EFFECTS = ("NOM", "ACC", "GEN", "IND", "SUBJ", "JUS")
_SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_REFERENCE = re.compile(r"^(\d{1,3}):(\d{1,3})(?::(\d{1,3}))?$")
_FAMILY = "FAM:"


class InvalidParticleData(ValueError):
    """A stored particle that must not reach a learner; the message names what is wrong."""


@dataclass(frozen=True)
class Text:
    """One learner-facing text, in every language the section is written in."""

    bs: str
    en: str

    def in_language(self, code: str) -> str:
        return self.bs if code == "bs" else self.en


@dataclass(frozen=True)
class CorpusTag:
    """How the corpus files one use of a particle: its tag, and its family where it gives one
    (لا of absolute negation is NEG|FAM:إِنّ — it works like إِنَّ)."""

    tag: str
    family: str | None = None

    @classmethod
    def parse(cls, text: str) -> CorpusTag:
        """"NEG" or "NEG|FAM:إِنّ", as the corpus writes it."""
        tag, _, family = text.partition("|")
        if not tag or (family and not family.startswith(_FAMILY)):
            raise InvalidParticleData(f"{text!r} is not a corpus tag (TAG or TAG|FAM:family)")
        return cls(tag, family.removeprefix(_FAMILY) or None)

    def __str__(self) -> str:
        return f"{self.tag}|{_FAMILY}{self.family}" if self.family else self.tag


@dataclass(frozen=True)
class ParticleOccurrence:
    """One particle at one place of the Quran, and what the next inflected word shows there."""

    lemma: str
    corpus_tag: CorpusTag
    surah: int
    ayah: int
    word: int
    marker: str | None       # NOM/ACC/GEN or IND/SUBJ/JUS; None when the next word shows neither

    @property
    def location(self) -> tuple[int, int, int]:
        return self.surah, self.ayah, self.word


@dataclass(frozen=True)
class Example:
    """An ayah that shows a use. `word` pins which word holds it, where the ayah holds the use twice."""

    surah: int
    ayah: int
    word: int | None
    why: Text

    @property
    def reference(self) -> str:
        return f"{self.surah}:{self.ayah}"


@dataclass(frozen=True)
class Use:
    key: str                     # the use's anchor on the page: "relative"
    kind: str                    # one of KINDS
    tags: tuple[CorpusTag, ...]  # how the corpus files this use
    title: Text
    explanation: Text
    effect: str | None           # one of EFFECTS: what the next word shows, held to every example
    ayat: tuple[Example, ...]


@dataclass(frozen=True)
class Particle:
    slug: str
    arabic: str                  # with harakat, a proclitic with a tatweel: بِـ
    lemma: str                   # the corpus's LEM: "ب", "مِن", "ما"
    count: int                   # how often the corpus files it under the uses shown
    meaning: Text                # a short gloss: "u, na; o"
    grammar: Text                # what it does, in plain words
    preposition: str | None      # its fil.nouns.bosnian name ("fi") when it is one the noun engine renders
    sources: tuple[str, ...]     # the classical works the uses rest on, by name
    notes: tuple[str, ...]       # decisions taken, for the reviewer and the next batch
    uses: tuple[Use, ...]
    spoken: str | None = None    # how the headword is voiced where that differs from how it is shown

    @property
    def said(self) -> str:
        return self.spoken or self.arabic.replace(TATWEEL, "")

    @property
    def corpus_tags(self) -> tuple[CorpusTag, ...]:
        """Every tag the uses cover, once each, in the order the uses name them."""
        return tuple(dict.fromkeys(tag for use in self.uses for tag in use.tags))

    @property
    def kinds(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(use.kind for use in self.uses))


# ---------------------------------------------------------------- parsing

def parse_particles(entries: Mapping[str, Mapping]) -> tuple[Particle, ...]:
    """Every particle, validated; the first problem stops the load with what and where."""
    particles = tuple(parse_particle(slug, entry) for slug, entry in entries.items())
    _refuse_duplicates("particles", [particle.arabic for particle in particles], "particle")
    return particles


def parse_particle(slug: str, entry: Mapping) -> Particle:
    if not _SLUG.match(slug):
        raise InvalidParticleData(f"{slug!r}: a particle's key is its page slug — lowercase latin letters, digits, hyphens")
    count = _required(slug, entry, "count")
    if not isinstance(count, int) or count < 1:
        raise InvalidParticleData(f"{slug}: `count` must be the corpus's count, a positive whole number")
    uses = tuple(_use(slug, item) for item in _required(slug, entry, "uses"))
    if not uses:
        raise InvalidParticleData(f"{slug}: a particle needs at least one use")
    _refuse_duplicates(slug, [use.key for use in uses], "use")
    sources = tuple(_required(slug, entry, "sources"))
    if not sources or not all(isinstance(source, str) and source.strip() for source in sources):
        raise InvalidParticleData(f"{slug}: name the classical works the particle's uses rest on in `sources`")
    return Particle(slug=slug, arabic=_required(slug, entry, "arabic"), lemma=_required(slug, entry, "lemma"),
                    count=count, meaning=_text(slug, entry, "meaning"), grammar=_text(slug, entry, "grammar"),
                    preposition=_preposition(slug, entry), sources=sources, notes=tuple(entry.get("notes", ())),
                    uses=uses, spoken=_spoken(slug, entry))


def _use(slug: str, entry: Mapping) -> Use:
    key = _required(slug, entry, "key")
    where = f"{slug} use {key}"
    if not isinstance(key, str) or not _SLUG.match(key):
        raise InvalidParticleData(f"{where}: a use's key is lowercase latin letters, digits, hyphens")
    kind = _required(where, entry, "kind")
    if kind not in KINDS:
        raise InvalidParticleData(f"{where}: kind {kind!r} is not one of {KINDS}")
    tags = tuple(CorpusTag.parse(tag) for tag in _required(where, entry, "tags"))
    if not tags:
        raise InvalidParticleData(f"{where}: name the corpus tags this use is filed under")
    effect = entry.get("effect")
    if effect is not None and effect not in EFFECTS:
        raise InvalidParticleData(f"{where}: effect {effect!r} is not one of {EFFECTS}")
    ayat = tuple(_example(where, item) for item in _required(where, entry, "ayat"))
    if not MIN_AYAT <= len(ayat) <= MAX_AYAT:
        raise InvalidParticleData(f"{where}: cite {MIN_AYAT}–{MAX_AYAT} ayat, not {len(ayat)}")
    _refuse_duplicates(where, [example.reference for example in ayat], "ayah")
    return Use(key=key, kind=kind, tags=tags, title=_text(where, entry, "title"),
               explanation=_text(where, entry, "explanation"), effect=effect, ayat=ayat)


def _example(where: str, entry: Mapping) -> Example:
    reference = _required(where, entry, "ref")
    found = _REFERENCE.match(reference) if isinstance(reference, str) else None
    if not found:
        raise InvalidParticleData(f"{where}: {reference!r} is not an ayah reference surah:ayah or surah:ayah:word")
    word = int(found.group(3)) if found.group(3) else None
    return Example(int(found.group(1)), int(found.group(2)), word, _text(f"{where} {reference}", entry, "why"))


def _preposition(slug: str, entry: Mapping) -> str | None:
    name = entry.get("preposition")
    if name is not None and name not in ARABIC_PREPOSITIONS:
        raise InvalidParticleData(f"{slug}: preposition {name!r} is not one the noun engine renders "
                                  f"({', '.join(ARABIC_PREPOSITIONS)})")
    return name


def _spoken(where: str, entry: Mapping) -> str | None:
    spoken = entry.get("spoken")
    if spoken is not None and (not isinstance(spoken, str) or not spoken.strip()):
        raise InvalidParticleData(f"{where}: `spoken` is the headword as voiced — leave it out or write it")
    return spoken


def _text(where: str, entry: Mapping, field: str) -> Text:
    """A learner-facing text: present and non-empty in every language."""
    value = _required(where, entry, field)
    missing = [code for code in LANGUAGES if not isinstance(value, Mapping) or not str(value.get(code, "")).strip()]
    if missing:
        raise InvalidParticleData(f"{where}: `{field}` has no {' or '.join(missing)} text")
    return Text(bs=value["bs"].strip(), en=value["en"].strip())


def _required(where: str, entry: Mapping, field: str):
    if field not in entry:
        raise InvalidParticleData(f"{where}: `{field}` is missing")
    return entry[field]


def _refuse_duplicates(where: str, values: Sequence[str], what: str) -> None:
    repeated = sorted({value for value in values if values.count(value) > 1})
    if repeated:
        raise InvalidParticleData(f"{where}: the same {what} twice: {repeated}")
