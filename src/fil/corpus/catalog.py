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

# The corpus tags a few verbs with a lemma that is not their citation form, and the
# lemma is what the generator conjugates from. For Form IV of غني every occurrence
# carries أَغْنَتْ (a 3fs past), so the table came out as أَغْنَتَ / أَغْنِتْ; its
# citation form is أَغْنَى (cf. 69:28 مَا أَغْنَىٰ عَنِّى مَالِيَهْ).
# Others carry a present (يَضُرَّ, يَفْقَهُ, يَتَفَكَّرُ, أُعِيدُ), passive (أُخْفِيَ, ذُكِّرَ)
# or jussive/imperative (مَتَّعْ) form: the card would show it as the headline and the
# generator conjugates nonsense from it (يِتْفَكَّرَ, أَعْيَدَ) or nothing at all.
_LEMMA_CORRECTIONS: dict[tuple[str, int], str] = {
    ("غني", 4): "أَغْنَى",
    ("ضرر", 1): "ضَرَّ",
    ("فقه", 1): "فَقِهَ",
    ("خفي", 4): "أَخْفَى",
    ("ذكر", 2): "ذَكَّرَ",
    ("عود", 4): "أَعَادَ",
    ("متع", 2): "مَتَّعَ",
    ("غرق", 4): "أَغْرَقَ",
    ("فكر", 5): "تَفَكَّرَ",
}


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
    lemma = _LEMMA_CORRECTIONS.get((root, form)) or _most_common_lemma(occurrences)
    ayat = sorted({o.ayah_ref for o in occurrences}, key=_mushaf_order)
    return VerbEntry(
        root=root,
        form=form,
        lemma=lemma,
        occurrence_count=len(occurrences),
        ayat=tuple(ayat),
    )


def _most_common_lemma(occurrences: list[VerbOccurrence]) -> str:
    return Counter(o.lemma for o in occurrences).most_common(1)[0][0]


def _mushaf_order(ayah_ref: str) -> tuple[int, int]:
    """Sort key that orders "surah:ayah" by surah then ayah numerically."""
    surah, ayah = ayah_ref.split(":")
    return int(surah), int(ayah)
