"""The case table of a noun: definite × indefinite × NOM/ACC/GEN, for each number it has.

The Quran's own spelling fills a cell first. A cell it never uses is asked of a generator
(the `NounGenerator` port; CAMeL Tools at the edge), and what comes back must (1) have the
letters of the Quran's own word — the singular's, or the plural pattern the Quran uses
(CAMeL offers أَيَادٍ and أَيْدٍ for يَد; only أَيْدٍ is Quranic), (2) be one form, not a
choice, and (3) pass the gate (fil.nouns.gate). A cell that fails stays empty: a missing
cell is honest, a wrong one teaches an error.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import unicodedata
from collections.abc import Iterable, Sequence
from typing import Protocol

from fil.nouns import gate
from fil.nouns.catalogue import plural_kind, plural_pattern
from fil.nouns.model import (ATTESTED, BROKEN, DEFINITE, DUAL, GENERATED, INDEFINITE, MISSING, PLURAL, SINGULAR, Cell,
                             NounLemma, NounOccurrence, Paradigm, ParadigmCell, table_cells)
from fil.nouns.spelling import skeleton, spelling_key, standalone, without_article

_FATHATAN = chr(0x064B)
_ARTICLE_LETTERS = ("ٱ", "ا")


class NounGenerator(Protocol):
    """Declines a lemma into one cell; every candidate it knows, best first, or none."""

    def generate(self, lemma: NounLemma, cell: Cell) -> tuple[str, ...]: ...


def build_paradigm(lemma: NounLemma, occurrences: Sequence[NounOccurrence],
                   generator: NounGenerator | None = None) -> Paradigm:
    attested = attested_cells(occurrences)
    patterns = _plural_patterns(lemma)
    cells = tuple(_cell(lemma, cell, attested, patterns, generator) for cell in table_cells(lemma.numbers))
    return Paradigm(lemma.lemma, lemma.root, cells)


def attested_cells(occurrences: Iterable[NounOccurrence]) -> dict[Cell, tuple[str, ...]]:
    """The Quran's spellings of each cell, commonest first, from words whose stem stands unchanged."""
    spellings: dict[Cell, Counter[str]] = defaultdict(Counter)
    for occurrence in occurrences:
        text = _cell_text(occurrence)
        if text is not None:
            spellings[Cell(occurrence.number, occurrence.state, occurrence.case)][text] += 1
    return {cell: tuple(text for text, _count in counts.most_common()) for cell, counts in spellings.items()}


def _cell_text(occurrence: NounOccurrence) -> str | None:
    """The cell as written alone, or None when this occurrence cannot show it.

    A possessor changes the stem (مُؤْمِنُو + هُم), and after لِ the article loses its alif
    (لِلنَّاسِ) — neither is the dictionary cell. Other proclitics leave the stem alone.
    """
    parts = occurrence.parts
    if parts is None or parts.possessive is not None or occurrence.case is None:
        return None
    if occurrence.state == INDEFINITE:
        return standalone(occurrence.stem)
    if occurrence.state != DEFINITE:
        return None
    article = _article(occurrence)
    return article + occurrence.stem if article else None


def _article(occurrence: NounOccurrence) -> str | None:
    """The article as the word writes it, when it is written in full (ٱلْ / ٱل)."""
    start = occurrence.word_text.rfind(occurrence.stem)
    before = occurrence.word_text[:start]
    index = max(before.rfind(letter) for letter in _ARTICLE_LETTERS)
    return before[index:] if index >= 0 and before[index + 1:index + 2] == "ل" else None


# ------------------------------------------------------------------ one cell

def _cell(lemma: NounLemma, cell: Cell, attested: dict[Cell, tuple[str, ...]], patterns: frozenset[str],
          generator: NounGenerator | None) -> ParadigmCell:
    """The Quran's spelling when it passes the gate too: the corpus's case tag is sometimes
    not the word's case (38:45 tags the genitive ٱلْأَيْدِى accusative), and a spelling
    filed under the wrong cell must not fill it."""
    quranic = next((text for text in attested.get(cell, ())
                    if not gate.problems(text, cell, lemma.lemma) and _is_main_plural(lemma, cell, text, patterns)),
                   None)
    if quranic is not None:
        return ParadigmCell(cell, quranic, ATTESTED)
    if generator is None:
        return ParadigmCell(cell, None, MISSING, ("no generator",))
    return generated_cell(lemma, cell, generator.generate(lemma, cell), patterns)


def generated_cell(lemma: NounLemma, cell: Cell, candidates: Sequence[str], patterns: frozenset[str]) -> ParadigmCell:
    """The one candidate with the Quran's letters that passes the gate, or a refusal."""
    if not candidates:
        return ParadigmCell(cell, None, MISSING, ("not generated",))
    quranic = _distinct([form for form in candidates if _letters(lemma, cell, form) in patterns_for(lemma, cell, patterns)])
    if not quranic:
        return ParadigmCell(cell, None, MISSING, ("not the Quran's pattern",))
    if len(quranic) > 1:
        return ParadigmCell(cell, None, MISSING, ("ambiguous: " + " / ".join(quranic),))
    if not has_quranic_vowels(quranic[0], _vowel_model(lemma, cell), _sound_ending_length(lemma, cell)):
        return ParadigmCell(cell, None, MISSING, (f"vowels differ from the Quran's: {_vowel_model(lemma, cell)}",))
    found = gate.problems(quranic[0], cell, lemma.lemma)
    if found:
        return ParadigmCell(cell, None, MISSING, found)
    return ParadigmCell(cell, quranic[0], GENERATED)


def has_quranic_vowels(form: str, model: str, ending_length: int = 0) -> bool:
    """Does `form` vowel its stem like `model` does? Letters alone are not enough: CAMeL
    knows نَهْر where the Quran says نَهَر. The stem is compared up to its last letter,
    whose vowel is the case ending and whose shape the number may change (ة → ت); a sound
    plural's ending (`ending_length` letters: ـُونَ / ـِينَ, ـَات) is the case too."""
    stem, model_stem = _stem_letters(form), _stem_letters(model)
    shared = min(len(stem), len(model_stem)) - 1 - ending_length
    return shared > 0 and stem[:shared] == model_stem[:shared]


def _stem_letters(form: str) -> list[str]:
    """Each letter of the stem with the vowel marks on it, the article taken off."""
    text = spelling_key(_without_written_article(form))
    letters: list[str] = []
    for char in text:
        if letters and unicodedata.combining(char):
            letters[-1] += char
        else:
            letters.append(char)
    return letters


def _without_written_article(form: str) -> str:
    if not gate.has_article(form):
        return form
    after_lam = form[form.index("ل") + 1:]
    return standalone(after_lam[len(after_lam) - len(_without_leading_marks(after_lam)):])


def _without_leading_marks(text: str) -> str:
    return text[next((index for index, char in enumerate(text) if not unicodedata.combining(char)), len(text)):]


def _sound_ending_length(lemma: NounLemma, cell: Cell) -> int:
    is_sound_plural = cell.number == PLURAL and lemma.plurals and lemma.plurals[0].kind != BROKEN
    return 2 if is_sound_plural else 0


def _vowel_model(lemma: NounLemma, cell: Cell) -> str:
    """What the stem's vowels must follow: the lemma, or the Quran's own plural."""
    return lemma.plurals[0].text if cell.number == PLURAL and lemma.plurals else lemma.lemma


def patterns_for(lemma: NounLemma, cell: Cell, plural_patterns: frozenset[str]) -> frozenset[str]:
    """The letters a form of this number must have: the singular's, the dual's, the Quran's plurals."""
    singular = skeleton(lemma.lemma)
    if cell.number == SINGULAR:
        return frozenset({singular})
    if cell.number == DUAL:
        return frozenset({singular[:-1] + "ت" if singular.endswith("ة") else singular})
    return plural_patterns


def _letters(lemma: NounLemma, cell: Cell, form: str) -> str:
    """A form's letters with the article and the case/number ending taken off."""
    letters = without_article(skeleton(form))
    if _FATHATAN in form:
        letters = letters.removesuffix("ا")
    if cell.number == DUAL:
        return next((letters.removesuffix(ending) for ending in ("ان", "ين") if letters.endswith(ending)), letters)
    if cell.number == PLURAL:
        return plural_pattern(plural_kind(lemma.lemma, form), form)
    return letters


def _plural_patterns(lemma: NounLemma) -> frozenset[str]:
    """The table shows the Quran's commonest plural; a second one (كُفَّار beside كَافِرُون)
    is listed with the lemma's plurals but would make a cell a choice."""
    main = lemma.plurals[:1]
    return frozenset(plural_pattern(plural.kind, plural.text) for plural in main)


def _is_main_plural(lemma: NounLemma, cell: Cell, text: str, patterns: frozenset[str]) -> bool:
    return cell.number != PLURAL or _letters(lemma, cell, text) in patterns


def _distinct(forms: Iterable[str]) -> list[str]:
    kept: dict[str, str] = {}
    for form in forms:
        kept.setdefault(spelling_key(form), form)
    return list(kept.values())
