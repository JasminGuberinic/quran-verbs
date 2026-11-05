"""The gate a noun's practice sentence must pass: the noun, in the case its role demands.

A noun sentence shows one use of the noun — subject, object, after a preposition, or the
possessor in an iḍāfa — so its case is fixed by its role: NOM, ACC, GEN, GEN. The analyzer
cannot check a case ending (CAMeL reads الشَّجَرَةَ as nominative too: it does not hold a
word to its written vowels), so the noun is held to its own case table instead: the target
word, with at most one attached proclitic taken off, must be a cell of the noun's table
letter for letter and vowel for vowel, and that cell's case must be the role's. The role's
setting is checked too: a preposition before it, or a noun in construct state (no article,
no nunation) before a possessor.

The other layers are the verbs' (fil.examples): every word analyzable, every gloss one the
lexicon gives. Results are recorded in the same ExampleChecks, read for a noun:
verb_root = "the target is this noun", verb_form = "in the role's case and setting".

Pure: the analyzer and the table are passed in.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import replace

from fil.examples import Analyze, Example, ExampleChecks, ExampleWord, GlossExceptions, gloss_check
from fil.nouns.model import ACCUSATIVE, CONSTRUCT, GENITIVE, INDEFINITE, NOMINATIVE, Cell
from fil.nouns.spelling import skeleton, spelling_key

SUBJECT, OBJECT, PREPOSITION, POSSESSION = "subject", "object", "preposition", "possession"
ROLES = (SUBJECT, OBJECT, PREPOSITION, POSSESSION)
ROLE_CASES = {SUBJECT: NOMINATIVE, OBJECT: ACCUSATIVE, PREPOSITION: GENITIVE, POSSESSION: GENITIVE}
CHECKED_BY = "noun table"

_NUNATION = {"ً", "ٌ", "ٍ"}
# Proclitics a target may carry: the prepositions that join their noun, and the conjunctions.
_PREPOSITION_PREFIXES = ("بِ", "كَ")
_CONJUNCTION_PREFIXES = ("وَ", "فَ")
_LAM = "لِ"
# Prepositions written as words of their own, by their letters.
SEPARATE_PREPOSITIONS = frozenset({"في", "علي", "من", "ءلي", "عن", "مع"})   # as `skeleton` writes them

# The table a target is held to: spelling key of a text → every cell spelled so (الْعَصَا is
# all three cases; ٱلْمُؤْمِنِينَ the accusative and the genitive).
NounTable = Mapping[str, tuple[Cell, ...]]
_DAMMATAN, _FATHATAN, _KASRATAN = "\u064c", "\u064b", "\u064d"
_PLAIN_VOWELS = {_DAMMATAN: "\u064f", _FATHATAN: "\u064e", _KASRATAN: "\u0650"}


def table_index(cells: Sequence[tuple[Cell, str]]) -> dict[str, tuple[Cell, ...]]:
    """(cell, text) pairs → the lookup the gate uses, with each indefinite cell's construct
    form too: the noun possessed by the word after it (رَبُّ ٱلْبَيْتِ, بَابَ ٱلْبَيْتِ)."""
    index: dict[str, tuple[Cell, ...]] = {}
    for cell, text in [*cells, *_construct_cells(cells)]:
        key = spelling_key(text)
        index[key] = (*index.get(key, ()), cell)
    return index


def construct_form(indefinite: str) -> str | None:
    """رَبٌّ → رَبُّ, كِتَابًا → كِتَابَ: nunation becomes its plain vowel (and a seat alif goes).
    None for a form without nunation (a sound plural or a dual loses its nūn instead)."""
    text = unicodedata.normalize("NFC", indefinite)
    if text.endswith("ا" + _FATHATAN):        # كِتاباً: nunation written after its seat
        text = text[:-2] + _FATHATAN
    if text.endswith("ا") and _FATHATAN in _trailing_marks(text[:-1]):
        text = text[:-1]
    marks = _trailing_marks(text)
    nunation = next((mark for mark in marks if mark in _PLAIN_VOWELS), None)
    if nunation is None:
        return None
    body = text[:len(text) - len(marks)]
    return body + marks.replace(nunation, _PLAIN_VOWELS[nunation])


def _trailing_marks(text: str) -> str:
    return text[len(text.rstrip("".join(chr(code) for code in range(0x064B, 0x0653)))):]


def _construct_cells(cells: Sequence[tuple[Cell, str]]) -> list[tuple[Cell, str]]:
    """Only for a number whose nominative shows nunation on a consonant (رَبٌّ): the alif of
    عَصًا is the stem's own and stays in construct (عَصَا مُوسَى) — the letters cannot say which."""
    declined = {cell.number for cell, text in cells if cell.state == INDEFINITE and cell.case == NOMINATIVE
                and _DAMMATAN in _trailing_marks(unicodedata.normalize("NFC", text))}
    found = [(Cell(cell.number, CONSTRUCT, cell.case), construct_form(text)) for cell, text in cells
             if cell.state == INDEFINITE and cell.number in declined]
    return [(cell, text) for cell, text in found if text]


def checked(example: Example, role: str, table: NounTable, analyze: Analyze,
            gloss_exceptions: GlossExceptions | None = None) -> Example:
    return replace(example, checks=check_sentence(example, role, table, analyze, gloss_exceptions))


def check_sentence(example: Example, role: str, table: NounTable, analyze: Analyze,
                   gloss_exceptions: GlossExceptions | None = None) -> ExampleChecks:
    if role not in ROLES:
        raise ValueError(f"unknown role {role!r}; one of {', '.join(ROLES)}")
    position = next((index for index, word in enumerate(example.words) if word.is_target), None)
    if position is None:
        return ExampleChecks(verb_root=False, verb_form=None, all_words_valid=False)
    target = example.words[position]
    found = target_cell(target.arabic, table)
    analyses = {word: analyze(word.arabic) for word in example.words}
    agreement, conflicts, by_exception = gloss_check(analyses, gloss_exceptions or {})
    return ExampleChecks(
        verb_root=found is not None,
        verb_form=found is not None and _fits_role(role, found, example.words, position, analyze),
        all_words_valid=all(found_analyses or (word is target and found) for word, found_analyses in analyses.items()),
        gloss_agreement=agreement, gloss_conflicts=conflicts,
        verb_form_by=CHECKED_BY if found else "", glossed_by_exception=by_exception)


def target_cell(word: str, table: NounTable) -> tuple[tuple[Cell, ...], str] | None:
    """The table cells the word is, and the proclitic it carried ("" for none)."""
    for proclitic, rest in _readings(word):
        cells = table.get(spelling_key(rest))
        if cells:
            return cells, proclitic
    return None


def _readings(word: str) -> list[tuple[str, str]]:
    """The word as it stands, and with each proclitic it may carry taken off."""
    readings = [("", word)]
    for prefix in (*_CONJUNCTION_PREFIXES, *_PREPOSITION_PREFIXES):
        if word.startswith(prefix):
            readings.append((prefix, word[len(prefix):]))
    if word.startswith(_LAM):
        rest = word[len(_LAM):]
        # After لِ the article loses its alif (لِلْبَيْتِ, لِلنَّاسِ); the table decides which reading is a cell.
        readings += [(_LAM, rest), (_LAM, "ا" + rest)]
    return readings


def _fits_role(role: str, found: tuple[tuple[Cell, ...], str], words: Sequence[ExampleWord], position: int,
               analyze: Analyze) -> bool:
    cells, proclitic = found
    if all(cell.case != ROLE_CASES[role] for cell in cells):
        return False
    previous = words[position - 1].arabic if position else ""
    if role == PREPOSITION:
        return proclitic in (*_PREPOSITION_PREFIXES, _LAM) or skeleton(previous) in SEPARATE_PREPOSITIONS
    if role == POSSESSION:
        return proclitic == "" and _is_construct(previous, analyze)
    return proclitic not in (*_PREPOSITION_PREFIXES, _LAM)


def _is_construct(word: str, analyze: Analyze) -> bool:
    """A noun possessed by the word after it: in full vowelling, a noun with neither the
    article nor nunation (CAMeL does not always offer the construct reading: ضَوْءُ)."""
    if not word or skeleton(word).startswith("ال") or _NUNATION & set(word):
        return False
    return any(analysis.get("pos") in ("noun", "noun_quant", "noun_num", "adj") for analysis in analyze(word))
