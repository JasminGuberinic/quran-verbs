"""Aggregate verb occurrences into the verb catalogue.

One entry per (root, form): its lemma, how often it occurs, and every ayah it
appears in. This is the list of verbs to teach and the ayah references the app
shows — both taken from the corpus, never hand-typed.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable

from fil.corpus.parse import VerbOccurrence


@dataclass(frozen=True)
class VerbEntry:
    """A distinct Quranic verb (root + form), aggregated over its occurrences."""

    root: str
    form: int
    lemma: str
    occurrence_count: int
    ayat: tuple[str, ...]  # unique "surah:ayah", in mushaf order


def build_catalog(occurrences: Iterable[VerbOccurrence]) -> list[VerbEntry]:
    """Group occurrences by (root, form) and summarize, most frequent first."""
    grouped: dict[tuple[str, int], list[VerbOccurrence]] = defaultdict(list)
    for occurrence in occurrences:
        grouped[(occurrence.root, occurrence.form)].append(occurrence)

    entries = [_entry(root, form, occs) for (root, form), occs in grouped.items()]
    return sorted(entries, key=lambda e: (-e.occurrence_count, e.root, e.form))


def _entry(root: str, form: int, occurrences: list[VerbOccurrence]) -> VerbEntry:
    """Summarize all occurrences of one (root, form) into a catalogue entry."""
    lemma = Counter(o.lemma for o in occurrences).most_common(1)[0][0]
    ayat = sorted({o.ayah_ref for o in occurrences}, key=_mushaf_order)
    return VerbEntry(
        root=root,
        form=form,
        lemma=lemma,
        occurrence_count=len(occurrences),
        ayat=tuple(ayat),
    )


def _mushaf_order(ayah_ref: str) -> tuple[int, int]:
    """Sort key that orders "surah:ayah" by surah then ayah numerically."""
    surah, ayah = ayah_ref.split(":")
    return int(surah), int(ayah)
