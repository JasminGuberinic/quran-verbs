"""Documented spellings for cells the generator cannot give and the analyzer cannot read.

A handful of attested forms have no standard (imlāʾī) spelling in the engine: سَأَلَ is
irregular enough that the generator skips the verb, so its imperative exists only in the
Quran's Uthmani سْـَٔلِ; and زِدْ is short enough that the analyzer reads nothing in it. A
learner still needs to see and hear the plain form, and a practice sentence still needs a
spelling the gate can confirm. These are written down by hand — with the reason — rather
than loosened in code, so every exception is visible, reviewable, and stays one.

Pure: parsing and lookup only; the file is read by the service at the edge.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class SpellingOverride:
    """The standard spellings of one cell, and why they had to be written down."""

    spellings: tuple[str, ...]
    why: str


# {(root, form): {(tense, pronoun): override}}
Overrides = Mapping[tuple[str, int], Mapping[tuple[str, str], SpellingOverride]]


class OverrideFormatError(ValueError):
    """An override entry that is malformed or undocumented."""


def parse_overrides(raw: Mapping[str, Mapping[str, Mapping]]) -> Overrides:
    """`{"root_form": {"tense:pronoun": {"spellings": [...], "why": "..."}}}` → Overrides.

    Fails fast on a bad key, an empty spelling list or a missing reason: an override
    without its why is exactly the silent exception this file exists to prevent.
    """
    return {_verb_key(verb): {_cell_key(cell): _override(verb, cell, entry)
                              for cell, entry in cells.items()}
            for verb, cells in raw.items()}


def documented_spellings(overrides: Overrides, root: str, form: int,
                         tense: str, pronoun: str) -> tuple[str, ...]:
    """The documented spellings of one cell — empty when nothing was written down."""
    override = overrides.get((root, form), {}).get((tense, pronoun))
    return override.spellings if override else ()


def _verb_key(verb: str) -> tuple[str, int]:
    root, _, form = verb.rpartition("_")
    if not root or not form.isdigit():
        raise OverrideFormatError(f"{verb!r}: expected root_form, e.g. سأل_1")
    return root, int(form)


def _cell_key(cell: str) -> tuple[str, str]:
    tense, _, pronoun = cell.partition(":")
    if not tense or not pronoun:
        raise OverrideFormatError(f"{cell!r}: expected tense:pronoun, e.g. imperative:anta")
    return tense, pronoun


def _override(verb: str, cell: str, entry: Mapping) -> SpellingOverride:
    spellings = tuple(spelling for spelling in entry.get("spellings", ()) if spelling)
    why = entry.get("why", "").strip()
    if not spellings or not why:
        raise OverrideFormatError(f"{verb} {cell}: an override needs spellings and a why")
    return SpellingOverride(spellings, why)
