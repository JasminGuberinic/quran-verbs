"""Documented spellings for cells the generator gets wrong or cannot give — and cells
the language does not use at all.

A handful of attested forms have no standard (imlāʾī) spelling in the engine: سَأَلَ is
irregular enough that the generator skips the verb, so its imperative exists only in the
Quran's Uthmani سْـَٔلِ; and زِدْ is short enough that the analyzer reads nothing in it. A
learner still needs to see and hear the plain form, and a practice sentence still needs a
spelling the gate can confirm. These are written down by hand — with the reason — rather
than loosened in code, so every exception is visible, reviewable, and stays one.

A generator also conjugates every cell mechanically, including ones Arabic does not use:
the past of وَذَرَ (يَذَرُ, ذَرْ) was abandoned by the Arabs in favour of تَرَكَ, so وَذَرْتُ is a
form nobody says. Such a cell is written down as `"unused": true` — with the reason — and is
neither shown on the card nor offered in practice. A key `tense:*` covers a whole tense.

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


@dataclass(frozen=True)
class UnusedForm:
    """A cell the language does not use, and why."""

    why: str


ANY_PRONOUN = "*"

# {(root, form): {(tense, pronoun | "*"): override}}
Overrides = Mapping[tuple[str, int], Mapping[tuple[str, str], SpellingOverride | UnusedForm]]


class OverrideFormatError(ValueError):
    """An override entry that is malformed or undocumented."""


def parse_overrides(raw: Mapping[str, Mapping[str, Mapping]]) -> Overrides:
    """`{"root_form": {"tense:pronoun": {"spellings": [...] | "unused": true, "why": "..."}}}`
    → Overrides.

    Fails fast on a bad key, an empty spelling list, an entry that is both unused and
    spelled, or a missing reason: an override
    without its why is exactly the silent exception this file exists to prevent.
    """
    return {_verb_key(verb): {_cell_key(cell): _override(verb, cell, entry)
                              for cell, entry in cells.items()}
            for verb, cells in raw.items()}


def documented_spellings(overrides: Overrides, root: str, form: int,
                         tense: str, pronoun: str) -> tuple[str, ...]:
    """The documented spellings of one cell — empty when nothing was written down."""
    override = overrides.get((root, form), {}).get((tense, pronoun))
    return override.spellings if isinstance(override, SpellingOverride) else ()


def is_unused(overrides: Overrides, root: str, form: int, tense: str, pronoun: str) -> bool:
    """Whether the language does not use this cell (by itself or by its whole tense)."""
    cells = overrides.get((root, form), {})
    return any(isinstance(cells.get((tense, key)), UnusedForm) for key in (pronoun, ANY_PRONOUN))


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


def _override(verb: str, cell: str, entry: Mapping) -> SpellingOverride | UnusedForm:
    spellings = tuple(spelling for spelling in entry.get("spellings", ()) if spelling)
    why = entry.get("why", "").strip()
    if not why:
        raise OverrideFormatError(f"{verb} {cell}: an override needs a why")
    if entry.get("unused") is True:
        if spellings:
            raise OverrideFormatError(f"{verb} {cell}: an unused cell has no spellings")
        return UnusedForm(why)
    if not spellings:
        raise OverrideFormatError(f"{verb} {cell}: an override needs spellings (or \"unused\": true)")
    if cell.endswith(":" + ANY_PRONOUN):
        raise OverrideFormatError(f"{verb} {cell}: spellings belong to one cell, not a whole tense")
    return SpellingOverride(spellings, why)
