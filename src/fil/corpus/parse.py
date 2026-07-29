"""Parse QAC morphology into structured verb occurrences (full, reconstructed).

Line format (tab-separated): `location  surface  pos  features`, e.g.
    2:6:3:1   كَفَرُ   V   PERF|VF:1|ROOT:كفر|LEM:كَفَرَ|3MP
    2:6:3:2   وا۟      N   PRON|SUFF|3MP

Crucially, QAC splits the subject-pronoun suffix into its own segment, so the
verb segment's surface is only the STEM (كَفَرُ). To get the full conjugated form
(كَفَرُوا۟) we stitch the verb stem to the following subject-pronoun suffix whose
person/gender/number matches the verb. Proclitics (before the verb) and object
pronouns (different PGN) are excluded automatically.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from itertools import groupby
from typing import Iterator

_ASPECT_TO_TENSE = {"PERF": "past", "IMPF": "present", "IMPV": "imperative"}
_PGN = re.compile(r"^([123])([MF]?)([SDP])$")


@dataclass(frozen=True)
class Segment:
    """One raw morphology segment (a verb stem, a pronoun suffix, a particle…)."""

    surah: int
    ayah: int
    word: int
    index: int
    surface: str
    pos: str
    features: tuple[str, ...]

    @property
    def is_subject_pronoun_suffix(self) -> bool:
        return "PRON" in self.features and "SUFF" in self.features


@dataclass(frozen=True)
class VerbOccurrence:
    """One verb, fully reconstructed, as attested at one place in the Quran."""

    surah: int
    ayah: int
    word: int
    segment: int
    surface: str          # full conjugated form (stem + subject suffix)
    root: str
    lemma: str
    form: int             # 1..10
    tense: str            # "past" | "present" | "imperative"
    person: int
    gender: str | None
    number: str
    mood: str | None
    passive: bool
    clean: bool           # True if nothing follows the verb + its subject suffix

    @property
    def ayah_ref(self) -> str:
        return f"{self.surah}:{self.ayah}"


def parse_segment(line: str) -> Segment | None:
    """Decode one raw line into a Segment (None if malformed)."""
    parts = line.rstrip("\n").split("\t")
    if len(parts) != 4:
        return None
    location, surface, pos, feature_text = parts
    surah, ayah, word, index = (int(n) for n in location.split(":"))
    return Segment(surah, ayah, word, index, surface, pos, tuple(feature_text.split("|")))


def iter_segments(lines: Iterator[str]) -> Iterator[Segment]:
    """Yield every parseable Segment from the raw morphology lines."""
    return (segment for segment in map(parse_segment, lines) if segment is not None)


def iter_verb_occurrences(segments: Iterator[Segment]) -> Iterator[VerbOccurrence]:
    """Yield a fully-reconstructed VerbOccurrence for each verb in the corpus."""
    for _word, group in groupby(segments, key=lambda s: (s.surah, s.ayah, s.word)):
        yield from _verbs_in_word(list(group))


def parse_line(line: str) -> VerbOccurrence | None:
    """Parse a single verb line into an occurrence (stem only — no reconstruction).

    Kept for unit tests that check one line in isolation; the pipeline uses
    `iter_verb_occurrences`, which reconstructs full forms across segments.
    """
    segment = parse_segment(line)
    return _occurrence_from_segment(segment) if segment else None


def _verbs_in_word(segments: list[Segment]) -> Iterator[VerbOccurrence]:
    """Yield each verb in a word with its subject suffix stitched on.

    A verb is `clean` when nothing follows it beyond its subject suffix — no
    object pronoun, no energic nūn. Only clean occurrences are trustworthy as
    citation forms (an object pronoun drops the plural alif; the energic nūn
    changes the ending), so downstream we build the oracle from clean ones only.
    """
    for position, segment in enumerate(segments):
        occurrence = _occurrence_from_segment(segment)
        if occurrence is None:
            continue
        suffix, consumed = _subject_suffix(segments[position + 1:], occurrence)
        is_clean = position + consumed == len(segments) - 1
        yield replace(occurrence, surface=occurrence.surface + suffix, clean=is_clean)


def _subject_suffix(following: list[Segment], verb: VerbOccurrence) -> tuple[str, int]:
    """Return (the subject-pronoun suffix, segments consumed) — at most one.

    Only forms that actually carry an overt subject suffix take one; a 3rd-masc-
    singular verb has none, so a following pronoun there is an OBJECT (whose PGN
    can even coincide with the verb's, e.g. naṣara-hu). We therefore absorb only
    a single subject segment, and only when the verb's form expects one.
    """
    if not _takes_subject_suffix(verb):
        return "", 0
    if not following:
        return "", 0
    first = following[0]
    matches = first.is_subject_pronoun_suffix and _person_gender_number(
        first.features
    ) == (verb.person, verb.gender, verb.number)
    return (first.surface, 1) if matches else ("", 0)


def _takes_subject_suffix(verb: VerbOccurrence) -> bool:
    """Whether this verb form is written with a separate subject-pronoun segment.

    Duals and plurals always are; perfect 1st/2nd-person singular add ـتُ/ـتَ/ـتِ;
    the 2nd-fem-sing imperfect/imperative adds ـين/ـي. Everything else (notably
    3rd-masc/fem singular, and prefix-only imperfect singulars) does not.
    """
    if verb.number in ("D", "P"):
        return True
    if verb.tense == "past" and verb.person in (1, 2):
        return True
    return verb.person == 2 and verb.gender == "F" and verb.number == "S"


def _occurrence_from_segment(segment: Segment | None) -> VerbOccurrence | None:
    """Build a VerbOccurrence from a verb segment (None if it is not a verb)."""
    if segment is None or segment.pos != "V":
        return None
    features = list(segment.features)
    aspect = next((f for f in features if f in _ASPECT_TO_TENSE), None)
    if aspect is None:
        return None

    person, gender, number = _person_gender_number(features)
    return VerbOccurrence(
        surah=segment.surah, ayah=segment.ayah, word=segment.word, segment=segment.index,
        surface=segment.surface,
        root=_feature_value(features, "ROOT"),
        lemma=_feature_value(features, "LEM"),
        form=int(_feature_value(features, "VF") or 0),
        tense=_ASPECT_TO_TENSE[aspect],
        person=person, gender=gender, number=number,
        mood=_feature_value(features, "MOOD"),
        passive="PASS" in features,
        clean=True,  # a single segment in isolation; _verbs_in_word refines this
    )


def _feature_value(features: tuple[str, ...] | list[str], key: str) -> str | None:
    prefix = f"{key}:"
    return next((f[len(prefix):] for f in features if f.startswith(prefix)), None)


def _person_gender_number(features: tuple[str, ...] | list[str]) -> tuple[int, str | None, str]:
    for feature in features:
        match = _PGN.match(feature)
        if match:
            person, gender, number = match.groups()
            return int(person), gender or None, number
    raise ValueError(f"no person/gender/number tag in features: {features}")
