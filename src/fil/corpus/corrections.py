"""Documented corrections to the corpus: occurrences filed under the wrong verb.

The Quranic Arabic Corpus occasionally tags a word with the root of a different verb
that shares its letters. يَبْلَىٰ in 20:120 ("[a kingdom that] does not wear out") is
بَلِيَ, yet it is filed under بلو form I, the verb بَلَا "to test" — so the "test" card
showed that ayah as an example and counted يَبْلَى as an attested form of "to test".

Each correction names the word ("surah:ayah:word") and the verb it must not count
for, with the reason. The occurrence is dropped from that verb's attested cells,
counts and example ayat. Written down by hand rather than patched in code, so every
exception stays visible and reviewable.

Pure: parsing and filtering only; the file is read by the service at the edge.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cached_property
from typing import Iterable, Iterator, Mapping

from fil.corpus.parse import VerbOccurrence

_LOCATION = re.compile(r"^\d+:\d+:\d+$")


@dataclass(frozen=True)
class Misattribution:
    """One word the corpus files under a verb it does not belong to."""

    location: str  # "surah:ayah:word"
    root: str
    form: int
    why: str


@dataclass(frozen=True)
class CorpusCorrections:
    """Every documented misattribution, looked up by (location, root, form)."""

    misattributions: tuple[Misattribution, ...] = ()

    def excludes(self, occurrence: VerbOccurrence) -> bool:
        """Whether this occurrence must not count for the verb the corpus gives it."""
        return _identity(occurrence) in self._excluded

    @cached_property
    def _excluded(self) -> frozenset[tuple[str, str, int]]:
        return frozenset((m.location, m.root, m.form) for m in self.misattributions)


NO_CORRECTIONS = CorpusCorrections()


class CorrectionFormatError(ValueError):
    """A correction entry that is malformed or undocumented."""


def parse_corrections(raw: Mapping[str, Mapping[str, Mapping]]) -> CorpusCorrections:
    """`{"root_form": {"s:a:w": {"why": "..."}}}` → CorpusCorrections.

    Fails fast on a bad key or a missing reason: a correction without its why is
    exactly the silent exception this file exists to prevent.
    """
    return CorpusCorrections(tuple(
        _misattribution(verb, location, entry)
        for verb, locations in raw.items()
        for location, entry in locations.items()
    ))


def without_misattributed(occurrences: Iterable[VerbOccurrence],
                          corrections: CorpusCorrections) -> Iterator[VerbOccurrence]:
    """The occurrences, minus those a correction says belong to another verb."""
    return (occurrence for occurrence in occurrences if not corrections.excludes(occurrence))


def _identity(occurrence: VerbOccurrence) -> tuple[str, str, int]:
    location = f"{occurrence.surah}:{occurrence.ayah}:{occurrence.word}"
    return location, occurrence.root, occurrence.form


def _misattribution(verb: str, location: str, entry: Mapping) -> Misattribution:
    root, _, form = verb.rpartition("_")
    if not root or not form.isdigit():
        raise CorrectionFormatError(f"{verb!r}: expected root_form, e.g. بلو_1")
    if not _LOCATION.match(location):
        raise CorrectionFormatError(f"{verb} {location!r}: expected surah:ayah:word, e.g. 20:120:13")
    why = entry.get("why", "").strip()
    if not why:
        raise CorrectionFormatError(f"{verb} {location}: a correction needs a why")
    return Misattribution(location, root, int(form), why)
