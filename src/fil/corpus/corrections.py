"""Documented corrections to the corpus: occurrences it files under the wrong verb or tense.

The Quranic Arabic Corpus occasionally mis-tags a word. Two kinds are corrected here:

- **Misattribution** — the word belongs to a different verb that shares its letters.
  يَبْلَىٰ in 20:120 ("[a kingdom that] does not wear out") is بَلِيَ, yet it is filed
  under بلو form I, the verb بَلَا "to test" — so the "test" card showed that ayah as an
  example and counted يَبْلَى as an attested form of "to test". The occurrence is
  dropped from that verb's attested cells, counts and example ayat.
- **Wrong tense** — the word is the right verb in a different tense. يَسْعَىٰ in 79:22
  (ثُمَّ أَدْبَرَ يَسْعَىٰ) is a present indicative, yet it is tagged PERF, so it would
  count as a past form and show as a past-tense example. The occurrence is kept, with
  the tense (and, for a present, the mood) it actually has.

Each correction names the word ("surah:ayah:word") and the verb the corpus files it
under, with the reason; a wrong-tense entry also names the true `tense` (and `mood`).
Written down by hand rather than patched in code, so every exception stays visible
and reviewable, and applied in one place (`apply_corrections`) by everything that
reads the corpus.

Pure: parsing and transforming only; the file is read by the service at the edge.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from functools import cached_property
from typing import Iterable, Iterator, Mapping

from fil.corpus.parse import VerbOccurrence

_LOCATION = re.compile(r"^\d+:\d+:\d+$")
_TENSES = ("past", "present", "imperative")
_PRESENT_MOODS = ("IND", "SUBJ", "JUS")

WordIdentity = tuple[str, str, int]  # ("surah:ayah:word", root, form)


@dataclass(frozen=True)
class Misattribution:
    """One word the corpus files under a verb it does not belong to."""

    location: str  # "surah:ayah:word"
    root: str
    form: int
    why: str


@dataclass(frozen=True)
class TenseCorrection:
    """One word the corpus files under the right verb but the wrong tense."""

    location: str  # "surah:ayah:word"
    root: str
    form: int
    tense: str
    mood: str | None  # the present's mood; None for the past and the imperative
    why: str


@dataclass(frozen=True)
class CorpusCorrections:
    """Every documented correction, looked up by (location, root, form)."""

    misattributions: tuple[Misattribution, ...] = ()
    tense_corrections: tuple[TenseCorrection, ...] = ()

    def excludes(self, occurrence: VerbOccurrence) -> bool:
        """Whether this occurrence must not count for the verb the corpus gives it."""
        return _identity(occurrence) in self._excluded

    def corrected(self, occurrence: VerbOccurrence) -> VerbOccurrence:
        """The occurrence with its documented tense, or unchanged if none is documented."""
        correction = self._retensed.get(_identity(occurrence))
        if correction is None:
            return occurrence
        return replace(occurrence, tense=correction.tense, mood=correction.mood)

    @cached_property
    def _excluded(self) -> frozenset[WordIdentity]:
        return frozenset((m.location, m.root, m.form) for m in self.misattributions)

    @cached_property
    def _retensed(self) -> dict[WordIdentity, TenseCorrection]:
        return {(t.location, t.root, t.form): t for t in self.tense_corrections}


NO_CORRECTIONS = CorpusCorrections()


class CorrectionFormatError(ValueError):
    """A correction entry that is malformed or undocumented."""


def parse_corrections(raw: Mapping[str, Mapping[str, Mapping]]) -> CorpusCorrections:
    """`{"root_form": {"s:a:w": {"why": "...", ["tense": ..., "mood": ...]}}}` → CorpusCorrections.

    An entry with a `tense` is a wrong-tense correction; one without is a misattribution.
    Fails fast on a bad key, an unknown tense or mood, or a missing reason: a correction
    without its why is exactly the silent exception this file exists to prevent.
    """
    corrections = [
        _correction(verb, location, entry)
        for verb, locations in raw.items()
        for location, entry in locations.items()
    ]
    return CorpusCorrections(
        misattributions=tuple(c for c in corrections if isinstance(c, Misattribution)),
        tense_corrections=tuple(c for c in corrections if isinstance(c, TenseCorrection)),
    )


def apply_corrections(occurrences: Iterable[VerbOccurrence],
                      corrections: CorpusCorrections) -> Iterator[VerbOccurrence]:
    """The occurrences as the corrections say they are: misfiled ones dropped, tenses fixed."""
    return (corrections.corrected(occurrence)
            for occurrence in occurrences if not corrections.excludes(occurrence))


def _identity(occurrence: VerbOccurrence) -> WordIdentity:
    location = f"{occurrence.surah}:{occurrence.ayah}:{occurrence.word}"
    return location, occurrence.root, occurrence.form


def _correction(verb: str, location: str, entry: Mapping) -> Misattribution | TenseCorrection:
    root, _, form = verb.rpartition("_")
    if not root or not form.isdigit():
        raise CorrectionFormatError(f"{verb!r}: expected root_form, e.g. بلو_1")
    if not _LOCATION.match(location):
        raise CorrectionFormatError(f"{verb} {location!r}: expected surah:ayah:word, e.g. 20:120:13")
    why = entry.get("why", "").strip()
    if not why:
        raise CorrectionFormatError(f"{verb} {location}: a correction needs a why")
    if "tense" not in entry:
        return Misattribution(location, root, int(form), why)
    tense, mood = _tense_and_mood(f"{verb} {location}", entry)
    return TenseCorrection(location, root, int(form), tense, mood, why)


def _tense_and_mood(subject: str, entry: Mapping) -> tuple[str, str | None]:
    tense, mood = entry["tense"], entry.get("mood")
    if tense not in _TENSES:
        raise CorrectionFormatError(f"{subject}: tense must be one of {_TENSES}, not {tense!r}")
    if tense == "present" and mood not in _PRESENT_MOODS:
        raise CorrectionFormatError(f"{subject}: a present needs a mood, one of {_PRESENT_MOODS}")
    if tense != "present" and mood is not None:
        raise CorrectionFormatError(f"{subject}: only a present has a mood")
    return tense, mood
