"""A studied noun's full case table: one row per number, and a second plural its own row.

The paradigm (fil.nouns.paradigm) declines the Quran's commonest plural; a noun with a
second plural the Quran really uses (كَافِرُونَ and كُفَّار) gets that plural declined as a
row of its own, never mixed into the first. A row the gate leaves empty is not shown. Where the generator cannot
decline a noun at all (CAMeL writes a case vowel on the alif of عَصَا), a documented
spelling may fill a cell — gated like any other, and never over the Quran's own.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace

from fil.nouns import gate
from fil.nouns.model import (ATTESTED, DEFINITE, DUAL, MISSING, NUMBERS, PLURAL, SINGULAR, NounLemma, NounOccurrence, ParadigmCell,
                             table_cells)
from fil.nouns.spelling import spelling_key
from fil.nouns.paradigm import NounGenerator, build_paradigm
from fil.nouns.studied import SECOND_PLURAL, NounTable, TableRow, noun_key

DOCUMENTED = "documented"   # a cell spelled by hand where the generator fails (data/noun_overrides.json)
SECOND_PLURAL_MINIMUM = 2   # a plural seen once may be a corpus quirk; it is listed, not declined


def build_table(lemma: NounLemma, occurrences: Sequence[NounOccurrence], generator: NounGenerator | None) -> NounTable:
    paradigm = build_paradigm(lemma, occurrences, generator)
    main_plural = lemma.plurals[0].text if lemma.plurals else None
    rows = [TableRow(number, number, main_plural if number == PLURAL else None,
                     tuple(found for found in paradigm.cells if found.cell.number == number))
            for number in lemma.numbers]
    rows += _second_plural(lemma, occurrences, generator)
    singular = {spelling_key(found.text) for row in rows if row.number == SINGULAR for found in row.cells if found.text}
    kept = (row for row in rows if _has_text(row) and not _is_collective(row, singular))
    return NounTable(noun_key(lemma.lemma, lemma.root), tuple(kept))


def as_collective(table: NounTable) -> NounTable:
    """A collective's table (fil.nouns.relations): its own row and nothing it has no meaning
    for. إِبِل "camels" has no dual and no plural; a generated one would teach a word Arabic
    does not use. A plural the Quran itself says (أَعْنَاب of عِنَب, "vines") stays."""
    own, *others = table.rows
    kept = [row for row in others if row.number != DUAL and any(found.source == ATTESTED for found in row.cells)]
    return replace(table, rows=(own, *kept))


def as_proper_name(table: NounTable) -> NounTable:
    """A taught proper name's table (fil.nouns.selection.TAUGHT_PROPER_NOUNS): a name is definite
    by itself, so only its definite cells are shown — كَعْبَةٌ "a cube" is another word than
    الْكَعْبَةُ "the Kaaba". A row left with no cell is dropped."""
    rows = (replace(row, cells=tuple(found for found in row.cells if found.cell.state == DEFINITE)) for row in table.rows)
    return replace(table, rows=tuple(row for row in rows if _has_text(row)))


def with_documented(table: NounTable, documented: Mapping[str, Mapping[str, str]], lemma: str) -> NounTable:
    """The table with documented spellings in cells the generator could not fill (`documented`:
    "S|definite|NOM" → {"text", "why"}). A documented spelling passes the same gate; an
    attested cell is never overridden — the Quran's spelling is the ground truth."""
    rows = tuple(replace(row, cells=tuple(_documented(found, documented, lemma) for found in row.cells))
                 for row in table.rows)
    rows += _documented_rows(table, documented, lemma, {row.number for row in rows})
    return replace(table, rows=rows)


def _documented(found: ParadigmCell, documented: Mapping[str, Mapping[str, str]], lemma: str) -> ParadigmCell:
    entry = documented.get(found.cell.code)
    if entry is None or found.source == ATTESTED:
        return found
    problems = gate.problems(entry["text"], found.cell, lemma)
    if problems:
        raise ValueError(f"{lemma} {found.cell.code}: the documented {entry['text']} fails the gate: {problems}")
    return ParadigmCell(found.cell, entry["text"], DOCUMENTED)


def _documented_rows(table: NounTable, documented, lemma: str, numbers: set[str]) -> tuple[TableRow, ...]:
    """A number whose every cell was refused has no row yet; documented cells give it one."""
    wanted = sorted({code.split("|")[0] for code in documented} - numbers, key=NUMBERS.index)
    return tuple(TableRow(number, number, None, tuple(_documented(ParadigmCell(cell, None, MISSING), documented, lemma)
                                                       for cell in table_cells((number,))))
                 for number in wanted)


def _is_collective(row: TableRow, singular: set[str]) -> bool:
    """A "plural" spelled like the singular (طَيْرًا, نَخْلٍ) is the corpus tagging a collective
    plural in meaning; it has no pattern of its own to decline."""
    texts = {spelling_key(found.text) for found in row.cells if found.text}
    return row.number == PLURAL and texts <= singular


def _second_plural(lemma: NounLemma, occurrences: Sequence[NounOccurrence],
                   generator: NounGenerator | None) -> list[TableRow]:
    if len(lemma.plurals) < 2 or lemma.plurals[1].count < SECOND_PLURAL_MINIMUM:
        return []
    second = lemma.plurals[1]
    variant = replace(lemma, plurals=(second, *lemma.plurals[:1], *lemma.plurals[2:]), numbers=(PLURAL,))
    cells = build_paradigm(variant, occurrences, generator).cells
    return [TableRow(SECOND_PLURAL, PLURAL, second.text, cells)]


def _has_text(row: TableRow) -> bool:
    return any(found.source != MISSING for found in row.cells)
