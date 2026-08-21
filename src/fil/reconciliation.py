"""Reconcile one or more generated conjugation tables against the attested oracle.

This is the correctness core. For every cell we gather what the Quran attests and
what each independent generator produced, then assign a tier:

  - attested   — the Quran attests this cell and every generator agrees with it
                 (truth = the Quran's own surface); confidence 1.0
  - consensus  — the Quran does not attest it, but ≥2 independent generators agree;
                 confidence 0.9 — strong evidence without a human in the loop
  - generated  — the Quran does not attest it and only one generator produced it;
                 confidence 0.7
  - quarantined — a DISAGREEMENT to review: either the Quran attests it and a
                 generator differs, or generators disagree with each other; 0.0

Pure logic: it takes tables + attested cells and returns typed, tiered results —
no generator, no corpus I/O — so it is fully unit-testable.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

from fil.conjugation import ConjugationTable
from fil.corpus.oracle import AttestedCells

_CONFIDENCE = {"attested": 1.0, "consensus": 0.9, "generated": 0.7, "quarantined": 0.0}


@dataclass(frozen=True)
class ReconciledCell:
    """One conjugation cell after reconciliation across the Quran + generators."""

    tense: str
    pronoun: str
    arabic: str               # the form we ship (Quran's when attested, else the primary generator's)
    source: str               # attested | consensus | generated | quarantined
    quran_attested: bool      # does the Quran attest this cell
    generator_agrees: bool | None  # generators vs the Quran; None when not attested
    confidence: float
    primary_form: str         # the primary generator's raw form ("" if none produced it)
    alternatives: tuple[str, ...] = field(default_factory=tuple)  # differing forms, for review


def reconcile(tables: list[ConjugationTable], attested: AttestedCells) -> list[ReconciledCell]:
    """Tier every cell across all generators against the attested oracle.

    `tables` are the generators' outputs; tables[0] is the primary (its form is the
    one shipped for unattested cells). The list may hold a single table.
    """
    return [
        _reconcile_cell(tense, pronoun, _forms_at(tables, tense, pronoun), attested.get((tense, pronoun)))
        for tense, pronoun in _all_cells(tables, attested)
    ]


def _all_cells(tables: list[ConjugationTable], attested: AttestedCells) -> list[tuple[str, str]]:
    """Every (tense, pronoun) any generator produced or the Quran attests, in order."""
    seen: list[tuple[str, str]] = []
    for table in tables:
        for tense, pronoun_forms in table.items():
            for pronoun in pronoun_forms:
                _add_once(seen, (tense, pronoun))
    for cell in attested:
        _add_once(seen, cell)
    return seen


def _add_once(seen: list[tuple[str, str]], cell: tuple[str, str]) -> None:
    if cell not in seen:
        seen.append(cell)


def _forms_at(tables: list[ConjugationTable], tense: str, pronoun: str) -> list[str]:
    """Each generator's form for this cell, primary first, skipping absent ones."""
    return [table[tense][pronoun] for table in tables if pronoun in table.get(tense, {})]


def _reconcile_cell(tense: str, pronoun: str, forms: list[str], attested_form: str | None) -> ReconciledCell:
    if attested_form is not None:
        return _attested_cell(tense, pronoun, forms, attested_form)
    return _unattested_cell(tense, pronoun, forms)


def _attested_cell(tense: str, pronoun: str, forms: list[str], attested_form: str) -> ReconciledCell:
    """The Quran is truth here.

    A cell is confirmed if at least one generator reproduces the Quran's form — the
    Quran plus one independent generator is already strong. Only when EVERY generator
    disagrees do we quarantine it: then either our extraction misread the Quran or the
    generators share a bug, and we cannot tell which without review.
    """
    if not forms:
        return _cell(tense, pronoun, attested_form, "attested", True, None, "", ())
    agrees = any(forms_match(form, attested_form) for form in forms)
    source = "attested" if agrees else "quarantined"
    disagreeing = _distinct(form for form in forms if not forms_match(form, attested_form))
    return _cell(tense, pronoun, attested_form, source, True, agrees, forms[0], disagreeing)


def _unattested_cell(tense: str, pronoun: str, forms: list[str]) -> ReconciledCell:
    """No Quranic truth: rank by how many independent generators agree."""
    primary = forms[0] if forms else ""
    if len(forms) >= 2 and _all_agree(forms):
        source = "consensus"
    elif len(forms) >= 2:
        source = "quarantined"
    else:
        source = "generated"
    alternatives = () if source in ("consensus", "generated") else _distinct(forms[1:])
    return _cell(tense, pronoun, primary, source, False, None, primary, alternatives)


def _cell(tense, pronoun, arabic, source, quran_attested, generator_agrees, primary_form, alternatives):
    return ReconciledCell(
        tense=tense, pronoun=pronoun, arabic=arabic, source=source,
        quran_attested=quran_attested, generator_agrees=generator_agrees,
        confidence=_CONFIDENCE[source], primary_form=primary_form, alternatives=alternatives,
    )


def _all_agree(forms: list[str]) -> bool:
    return all(forms_match(forms[0], other) for other in forms[1:])


def _distinct(forms) -> tuple[str, ...]:
    """De-duplicate forms up to orthographic folding, preserving order."""
    kept: list[str] = []
    for form in forms:
        if not any(forms_match(form, seen) for seen in kept):
            kept.append(form)
    return tuple(kept)


_ALEF = "ا"
_YAA = "ي"
# Combining marks dropped for comparison: maddah, hamza-above/below (so أ/إ/ؤ/ئ fold
# to their base once NFD-decomposed), sukūn (Uthmani often omits it), and the Quran's
# annotation/pause marks. Short vowels (fatḥa/ḍamma/kasra) and shadda are KEPT.
_DROP = {0x0653, 0x0654, 0x0655, 0x0652} | set(range(0x06D6, 0x06EE))
_HARAKAT = range(0x064B, 0x0653)


def forms_match(a: str, b: str) -> bool:
    """Compare two Arabic forms up to *orthographic* variation, not vowels.

    Uthmani and imlāʾī spell the same form differently — alef-madda آ vs hamza+alef
    ءا, alef-maqṣūra ى vs yāʾ ي, hamzatu-l-waṣl, dagger alef, silent/pause marks. We
    fold those; genuine differences (a wrong letter or short vowel) still fail.
    """
    return _normalize(a) == _normalize(b)


def _normalize(form: str) -> str:
    text = _fold_orthography(unicodedata.normalize("NFD", form))
    text = _strip_leading_harakat(text)
    if len(text) >= 2 and text[0] == _ALEF and ord(text[1]) in _HARAKAT:
        text = text[0] + text[2:]  # imperative's initial connecting vowel
    return text


def _fold_orthography(decomposed: str) -> str:
    """Unify the alef/hamza/yāʾ families and drop orthographic-only marks."""
    folded: list[str] = []
    for char in decomposed:
        code = ord(char)
        if code in _DROP or code == 0x0621:      # marks + standalone hamza
            continue
        if code == 0x0670:                       # dagger alef — a letter, or a reading aid
            folded.extend(_dagger_alef(folded))
        elif code == 0x0671:                     # alef waṣl → alef
            folded.append(_ALEF)
        elif code == 0x0649:                     # alef maqṣūra → yāʾ
            folded.append(_YAA)
        else:
            folded.append(char)
    return "".join(folded)


def _dagger_alef(folded: list[str]) -> str:
    """What the superscript alef stands for, which depends on what precedes it.

    Uthmani uses the same mark for two different things. Over a consonant it stands in
    for an alef that is simply not written (سَمَٰوَات = سماوات), so it folds to one. But
    over a long vowel — an alef, or the alef maqṣūra we have just folded to yāʾ — it is
    only a reading aid saying "pronounce this long" (يَرَىٰ = يرى); adding a letter there
    invents one, and the form then fails to match the same form spelled plainly.
    """
    return "" if _last_letter(folded) in (_ALEF, _YAA) else _ALEF


def _last_letter(folded: list[str]) -> str | None:
    """The most recent actual letter, looking past any vowel marks sitting on it."""
    return next((char for char in reversed(folded) if ord(char) not in _HARAKAT), None)


def _strip_leading_harakat(text: str) -> str:
    """Drop harakāt orphaned at the start (e.g. the vowel left by a removed hamza)."""
    index = 0
    while index < len(text) and ord(text[index]) in _HARAKAT:
        index += 1
    return text[index:]


def tier_counts(cells: list[ReconciledCell]) -> dict[str, int]:
    """How many cells fell into each tier."""
    counts = {"attested": 0, "consensus": 0, "generated": 0, "quarantined": 0}
    for cell in cells:
        counts[cell.source] += 1
    return counts
