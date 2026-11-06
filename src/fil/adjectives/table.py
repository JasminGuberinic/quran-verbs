"""An adjective's two case tables, masculine and feminine, built with the nouns' engine.

Each side is declined like a noun (fil.nouns.table.build_table): the Quran's spellings fill
their cells first, CAMeL the cells the Quran does not use, and every form passes the noun
gate. CAMeL's lexicon lacks many adjectives' plurals (كَبِير has neither كِبَار nor كَبِيرَات)
and a few adjectives altogether, so a second generator follows: the rule
(fil.adjectives.declension), which declines what is regular and refuses the rest. What the
rule makes passes the same gate; what neither can make stays empty.

The sides differ in what they start from:

  - the masculine from the lemma's masculine occurrences; its plural is the Quran's when it
    has one, else what the meaning says (fil.adjectives.model): none, the sound plural
    (-ūna), or a broken plural written once by the drafter (كِبَار);
  - the feminine from the lemma's feminine occurrences and, when the corpus lemmatises the
    feminine on its own (كَثِيرَة), from those; its plural is the Quran's, else the sound -āt.

CAMeL is asked for one gender at a time (`GenderedGenerator`): asked for a masculine plural
it does not know, it would otherwise answer with the feminine one (عَظِيمَاتٌ).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from fil.adjectives.declension import CannotDecline, declined_number
from fil.adjectives.model import NO_PLURAL, SOUND_PLURAL, AdjectiveMeaning, AdjectiveTable
from fil.nouns import gate
from fil.nouns.catalogue import plural_pattern, plurals_of
from fil.nouns.model import (BROKEN, DUAL, FEMININE, MASCULINE, MISSING, NUMBERS, PLURAL, SINGULAR, SOUND_FEMININE,
                             SOUND_MASCULINE, Cell, NounLemma, NounOccurrence, ParadigmCell, PluralForm, table_cells)
from fil.nouns.paradigm import NounGenerator
from fil.nouns.studied import NounTable, TableRow
from fil.nouns.table import DOCUMENTED, build_table

RULE = "rule"          # a cell declined by fil.adjectives.declension (shown as a standard form, like CAMeL's)
DIPTOTE_PATTERNS = ("أَفْعَل", "فَعْلَان")   # singulars without nunation: آخَرُ, أَبْيَضُ


class GenderedGenerator:
    """A NounGenerator asked for one gender of the masculine lex: CAMeL declines كَبِيرَة as the
    feminine of كَبِير, so the feminine side passes the masculine lemma with gender F."""

    def __init__(self, generator: NounGenerator, masculine: str, gender: str) -> None:
        self._generator, self._masculine, self._gender = generator, masculine, gender

    def generate(self, lemma: NounLemma, cell: Cell) -> tuple[str, ...]:
        return self._generator.generate(replace(lemma, lemma=self._masculine, gender=self._gender), cell)


def build_adjective_table(lemma: NounLemma, meaning: AdjectiveMeaning, occurrences: Sequence[NounOccurrence],
                          feminine_occurrences: Sequence[NounOccurrence], generator: NounGenerator | None) -> AdjectiveTable:
    """`occurrences` are the lemma's own; `feminine_occurrences` those of its separately lemmatised feminine."""
    masculine = [occurrence for occurrence in occurrences if occurrence.gender != FEMININE]
    feminine = [*(occurrence for occurrence in occurrences if occurrence.gender == FEMININE), *feminine_occurrences]
    return AdjectiveTable(meaning.key, _masculine_table(lemma, meaning, masculine, generator),
                          _feminine_table(lemma, meaning, feminine, generator))


# ---------------------------------------------------------------- the two sides

def _masculine_table(lemma: NounLemma, meaning: AdjectiveMeaning, occurrences: Sequence[NounOccurrence],
                     generator: NounGenerator | None) -> NounTable:
    quranic = plurals_of(lemma.lemma, occurrences)
    has_plural = bool(quranic) or meaning.masculine_plural != NO_PLURAL
    numbers = (SINGULAR, DUAL, PLURAL) if has_plural else (SINGULAR, DUAL)
    side = replace(lemma, gender=MASCULINE, plurals=quranic, numbers=numbers)
    table = build_table(side, occurrences, _gendered(generator, lemma.lemma, MASCULINE))
    plural = _rule_plural(quranic, SOUND_MASCULINE, meaning.masculine_plural)
    return with_rule_cells(table, lemma.lemma, numbers, plural, is_diptote_singular=meaning.pattern in DIPTOTE_PATTERNS)


def _feminine_table(lemma: NounLemma, meaning: AdjectiveMeaning, occurrences: Sequence[NounOccurrence],
                    generator: NounGenerator | None) -> NounTable:
    """A side of its own, spelled from the feminine (كَبِيرَة): its letters are what the gate
    and the pattern check compare a generated form with."""
    quranic = plurals_of(meaning.feminine, occurrences)
    side = replace(lemma, lemma=meaning.feminine, gender=FEMININE, plurals=quranic, numbers=NUMBERS, forms=(),
                   dual_count=0)
    table = build_table(side, _as_feminine_lemma(occurrences, meaning.feminine),
                        _gendered(generator, lemma.lemma, FEMININE))
    plural = _rule_plural(quranic, SOUND_FEMININE, None if quranic else SOUND_PLURAL)
    return replace(with_rule_cells(table, meaning.feminine, NUMBERS, plural), key=meaning.key)


def _rule_plural(quranic: Sequence[PluralForm], sound_kind: str, wanted: str | None) -> str | None:
    """Which plural the rule may decline: the sound one where the Quran's is sound; where the
    Quran's is broken, the drafter's stem of that same pattern (its stem as the Quran writes it
    carries a case ending: عُلَمَٰٓؤُا۟) or none; else what the meaning asks for ("sound" or a stem)."""
    if not quranic:
        return None if wanted in (None, NO_PLURAL) else wanted
    if quranic[0].kind == sound_kind:
        return SOUND_PLURAL
    is_same_pattern = wanted not in (None, NO_PLURAL, SOUND_PLURAL) and \
        plural_pattern(BROKEN, wanted) == plural_pattern(BROKEN, quranic[0].text)
    return wanted if is_same_pattern else None


def _as_feminine_lemma(occurrences: Sequence[NounOccurrence], feminine: str) -> list[NounOccurrence]:
    """The paradigm reads a cell's plural kind against the lemma; feminine forms filed under the
    masculine lemma (كَثِيرَةً under كَثِير) are read against the feminine."""
    return [replace(occurrence, lemma=feminine) for occurrence in occurrences]


def _gendered(generator: NounGenerator | None, masculine: str, gender: str) -> NounGenerator | None:
    return GenderedGenerator(generator, masculine, gender) if generator else None


# ---------------------------------------------------------------- the rule after CAMeL

def with_rule_cells(table: NounTable, singular: str, numbers: Sequence[str], plural: str | None,
                    is_diptote_singular: bool = False) -> NounTable:
    """Every number wanted has a row; each empty cell the rule can decline is filled, gated.
    A broken plural stem written by the drafter fills its row as documented."""
    rows = {row.row: row for row in table.rows}
    for number in numbers:
        if number == PLURAL and plural is None:
            continue
        row = rows.get(number) or TableRow(number, number, _row_plural(plural), _empty(number))
        rows[number] = _filled(row, singular, plural, is_diptote_singular)
    kept = tuple(row for row in rows.values() if any(found.text for found in row.cells))
    return in_reading_order(replace(table, rows=kept))


def in_reading_order(table: NounTable) -> NounTable:
    """Singular, dual, plural, then a second plural — however the rows were added."""
    order = {name: index for index, name in enumerate(NUMBERS)}
    return replace(table, rows=tuple(sorted(table.rows, key=lambda row: (order.get(row.row, len(order)), row.row))))


def _filled(row: TableRow, singular: str, plural: str | None, is_diptote_singular: bool) -> TableRow:
    try:
        forms = declined_number(singular, row.number, plural, is_diptote_singular)
    except CannotDecline:
        return row
    source = DOCUMENTED if row.number == PLURAL and plural not in (None, SOUND_PLURAL) else RULE
    return replace(row, cells=tuple(found if found.text else _gated(found.cell, forms[(found.cell.state, found.cell.case)],
                                                                    singular, source)
                                    for found in row.cells))


def _gated(cell: Cell, text: str, lemma: str, source: str) -> ParadigmCell:
    problems = gate.problems(text, cell, lemma)
    if problems:
        return ParadigmCell(cell, None, MISSING, problems)
    return ParadigmCell(cell, text, source)


def _empty(number: str) -> tuple[ParadigmCell, ...]:
    return tuple(ParadigmCell(cell, None, MISSING, ("not generated",)) for cell in table_cells((number,)))


def _row_plural(plural: str | None) -> str | None:
    return plural if plural not in (None, SOUND_PLURAL) else None
