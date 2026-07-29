"""Build the attested-conjugation oracle from QAC occurrences.

A QAC verb segment's surface IS a clean conjugated form (proclitics like wa-/fa-
and object-pronoun enclitics are separate segments), so the corpus hands us
ground-truth conjugation cells straight from the Quran. We key them the same way
the engine's conjugation tables are keyed — (tense, pronoun) — for the ACTIVE
voice and, for the present, the indicative mood (the citation form we teach).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable

from fil.corpus.parse import VerbOccurrence

# (person, gender, number) → the pronoun key the engine uses. Duals are genderless
# in the verb, so 2MD/2FD/2D all map to antuma, and 3MD/3FD/3D to huma.
_PRONOUN_BY_PGN: dict[tuple[int, str | None, str], str] = {
    (1, None, "S"): "ana", (1, None, "P"): "nahnu",
    (2, "M", "S"): "anta", (2, "F", "S"): "anti",
    (2, "M", "P"): "antum", (2, "F", "P"): "antunna",
    (3, "M", "S"): "huwa", (3, "F", "S"): "hiya",
    (3, "M", "P"): "hum", (3, "F", "P"): "hunna",
}
_DUAL_PRONOUN = {2: "antuma", 3: "huma"}

# Per (root, form): the attested surface for each (tense, pronoun) cell.
AttestedCells = dict[tuple[str, str], str]


def build_oracle(occurrences: Iterable[VerbOccurrence]) -> dict[tuple[str, int], AttestedCells]:
    """Return {(root, form): {(tense, pronoun): attested_surface}}.

    Only teachable cells are kept: active voice, and present only in the
    indicative mood. When a cell is attested by several spellings, the most
    frequent one wins.
    """
    surfaces: dict[tuple[str, int], dict[tuple[str, str], Counter]] = defaultdict(
        lambda: defaultdict(Counter)
    )
    for occ in filter(_is_teachable, occurrences):
        pronoun = _pronoun_of(occ)
        surfaces[(occ.root, occ.form)][(occ.tense, pronoun)][occ.surface] += 1

    return {
        verb: {cell: counts.most_common(1)[0][0] for cell, counts in cells.items()}
        for verb, cells in surfaces.items()
    }


def _is_teachable(occ: VerbOccurrence) -> bool:
    """A trustworthy citation: clean, active, present only in the indicative.

    `clean` excludes occurrences with a trailing object pronoun or energic nūn,
    whose surface is not the plain citation form.
    """
    if not occ.clean:
        return False
    if occ.passive:
        return False
    if occ.tense == "present" and occ.mood not in (None, "IND"):
        return False
    return True


def _pronoun_of(occ: VerbOccurrence) -> str:
    """Map an occurrence's person/gender/number to a pronoun key (duals merged)."""
    if occ.number == "D":
        return _DUAL_PRONOUN[occ.person]
    return _PRONOUN_BY_PGN[(occ.person, occ.gender, occ.number)]
