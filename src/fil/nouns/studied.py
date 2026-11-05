"""A studied noun's own data: its meaning, its case table, its practice sentences.

The catalogue (fil.nouns.catalogue) knows every noun of the Quran; a noun becomes studied
when it is given a meaning — in English and Bosnian, with the iḍāfa example its card shows.
Its case table is then computed once (Quranic spellings first, gated CAMeL forms for the
rest; fil.nouns.paradigm) and stored, so that the pages, the sentence gate and a reviewer
all read the same table. Pure: parsing and validation; files are read at the edge
(fil.noun_store).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from fil.examples import Example
from fil.nouns.explanation import Idafa
from fil.nouns import bosnian
from fil.nouns.model import CASES, DUAL, NUMBERS, PLURAL, SINGULAR, STATES, Cell, ParadigmCell

SECOND_PLURAL = "P2"
_BOSNIAN_NUMBERS = {SINGULAR: bosnian.SINGULAR, DUAL: bosnian.DUAL, PLURAL: bosnian.PLURAL}   # the row of a second plural (كُفَّار beside كَافِرُون)


def noun_key(lemma: str, root: str) -> str:
    return f"{lemma}|{root}"


def split_key(key: str) -> tuple[str, str]:
    lemma, _separator, root = key.partition("|")
    return lemma, root


class InvalidNounData(ValueError):
    """A stored noun entry that must not reach a learner; the message names what is wrong."""


@dataclass(frozen=True)
class NounMeaning:
    lemma: str
    root: str
    en: str                     # "hand" — the first sense is the one forms are composed with
    en_plural: str              # "hands"
    bs: str                     # "ruka"
    is_countable: bool = True
    # Its bare accusative is mostly no object — an adverb (يَوْمَ "on the day", حَقًّا "truly") or a
    # call (رَبَّنَا "our Lord!") — so no bare accusative of it is glossed.
    is_accusative_adverbial: bool = False
    is_polysemous: bool = False             # عَيْن "eye" and "spring": one sense would mislead, no form is composed
    idafa: Idafa | None = None

    @property
    def key(self) -> str:
        return noun_key(self.lemma, self.root)

    @property
    def en_first(self) -> str:
        return self.en.split(",")[0].strip()

    @property
    def en_plural_first(self) -> str:
        return self.en_plural.split(",")[0].strip()


def parse_meaning(key: str, entry: Mapping) -> NounMeaning:
    lemma, root = split_key(key)
    missing = [field for field in ("en", "enPlural", "bs") if not str(entry.get(field, "")).strip()]
    if not root or missing:
        raise InvalidNounData(f"{key}: {'no root' if not root else 'missing ' + ', '.join(missing)}")
    return NounMeaning(lemma=lemma, root=root, en=entry["en"], en_plural=entry["enPlural"], bs=entry["bs"],
                       is_countable=entry.get("countable", True),
                       is_accusative_adverbial=entry.get("accusativeAdverbial", False),
                       is_polysemous=entry.get("polysemous", False),
                       idafa=_idafa(key, entry.get("idafa")))


def meaning_entry(meaning: NounMeaning) -> dict:
    entry = {"en": meaning.en, "enPlural": meaning.en_plural, "bs": meaning.bs, "countable": meaning.is_countable}
    if meaning.is_accusative_adverbial:
        entry["accusativeAdverbial"] = True
    if meaning.is_polysemous:
        entry["polysemous"] = True
    if meaning.idafa:
        entry["idafa"] = {"ar": meaning.idafa.arabic, "en": meaning.idafa.en, "bs": meaning.idafa.bs}
    return entry


def _idafa(key: str, entry: Mapping | None) -> Idafa | None:
    if not entry:
        return None
    if not all(str(entry.get(field, "")).strip() for field in ("ar", "en", "bs")):
        raise InvalidNounData(f"{key}: an iḍāfa example needs ar, en and bs")
    return Idafa(entry["ar"], entry["en"], entry["bs"])


# ------------------------------------------------------------------ the case table

@dataclass(frozen=True)
class TableRow:
    row: str                    # S, D, P, or P2 (a second plural)
    number: str                 # S, D, P
    plural: str | None          # the plural pattern this row declines, as the Quran writes it
    cells: tuple[ParadigmCell, ...]

    def text(self, state: str, case: str) -> str | None:
        return next((found.text for found in self.cells if found.cell.state == state and found.cell.case == case), None)


@dataclass(frozen=True)
class NounTable:
    key: str
    rows: tuple[TableRow, ...]

    def cells(self) -> tuple[tuple[Cell, str], ...]:
        """Every filled cell with its text (a second plural's under the plural's cell)."""
        return tuple((found.cell, found.text) for row in self.rows for found in row.cells if found.text)


def bosnian_numbers(table: NounTable) -> tuple[str, ...]:
    """The numbers a noun's Bosnian declension must have cells for: those its table shows."""
    return tuple(dict.fromkeys(_BOSNIAN_NUMBERS[row.number] for row in table.rows))


def parse_table(key: str, entry: Mapping) -> NounTable:
    try:
        return NounTable(key, tuple(_row(row) for row in entry["rows"]))
    except (KeyError, TypeError, ValueError) as problem:
        raise InvalidNounData(f"{key}: malformed table ({problem})") from problem


def table_entry(table: NounTable) -> dict:
    return {"rows": [{"row": row.row, "number": row.number, "plural": row.plural,
                      "cells": [{"state": found.cell.state, "case": found.cell.case, "text": found.text,
                                 "source": found.source, **({"problems": list(found.problems)} if found.problems else {})}
                                for found in row.cells]}
                     for row in table.rows]}


def _row(entry: Mapping) -> TableRow:
    number = entry["number"]
    if number not in NUMBERS:
        raise ValueError(f"no number {number!r}")
    cells = tuple(ParadigmCell(Cell(number, cell["state"], cell["case"]), cell["text"], cell["source"],
                               tuple(cell.get("problems", ())))
                  for cell in entry["cells"])
    if any(found.cell.state not in STATES or found.cell.case not in CASES for found in cells):
        raise ValueError("unknown state or case")
    return TableRow(entry["row"], number, entry.get("plural"), cells)


# ------------------------------------------------------------------ practice sentences

@dataclass(frozen=True)
class NounSentence:
    """One practice sentence showing the noun in one role (fil.nouns.sentence_gate.ROLES)."""

    key: str
    role: str
    example: Example
