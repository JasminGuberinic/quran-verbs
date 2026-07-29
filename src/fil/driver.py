"""Drive the generator for a QAC verb — without hand-authoring each one.

To conjugate a Form-I verb we need its present-tense stem vowel (a/i/u), which
the corpus does not tag. We infer it by fitting: generate with each candidate
vowel and keep the one whose present tense matches the form the Quran attests.
For derived forms (II–X) the pattern fixes the vowel, so any value works.

This is what lets the engine scale from a few hand-authored verbs to every verb
in the Quran, each still checked against attested truth downstream.
"""

from __future__ import annotations

from fil.conjugation import conjugate
from fil.models import Verb
from fil.corpus.catalog import VerbEntry
from fil.corpus.oracle import AttestedCells
from fil.reconciliation import forms_match

_CANDIDATE_VOWELS = ("a", "i", "u")


def build_verb(entry: VerbEntry, attested: AttestedCells) -> Verb | None:
    """Build a Verb ready for generation, or None if we cannot do so safely."""
    present_vowel = _present_vowel(entry, attested)
    if present_vowel is None:
        return None
    try:
        return Verb(
            id=f"{entry.root}_{entry.form}",
            root=entry.root,
            past3ms=entry.lemma,
            present_vowel=present_vowel,
            transitive=True,
            form=entry.form,
            glosses={"ar": entry.lemma},  # placeholder; real glosses come later
        )
    except ValueError:
        return None  # lemma not a valid vocalized input


def _present_vowel(entry: VerbEntry, attested: AttestedCells) -> str | None:
    """The present stem vowel: fixed by the pattern for II–X, inferred for I."""
    if entry.form != 1:
        return "u"  # ignored by the generator for derived forms
    return _infer_present_vowel(entry.lemma, attested)


def _infer_present_vowel(lemma: str, attested: AttestedCells) -> str | None:
    """Fit a/i/u to an attested present form; None if none fits (or none exists)."""
    pronoun, target = _reference_present(attested)
    if target is None:
        return None
    for vowel in _CANDIDATE_VOWELS:
        table = _safe_conjugate(lemma, vowel)
        if table and forms_match(table.get("present", {}).get(pronoun, ""), target):
            return vowel
    return None


def _reference_present(attested: AttestedCells) -> tuple[str, str | None]:
    """Pick an attested present cell to fit against (prefer huwa)."""
    present = {pronoun: surface for (tense, pronoun), surface in attested.items() if tense == "present"}
    if "huwa" in present:
        return "huwa", present["huwa"]
    if present:
        pronoun = sorted(present)[0]
        return pronoun, present[pronoun]
    return "huwa", None


def _safe_conjugate(lemma: str, vowel: str) -> dict[str, dict[str, str]] | None:
    """Conjugate a probe verb, returning None if the generator cannot handle it."""
    try:
        probe = Verb(
            id="_probe", root="_", past3ms=lemma, present_vowel=vowel,
            transitive=True, form=1, glosses={"ar": lemma},
        )
        return conjugate(probe)
    except Exception:  # noqa: BLE001 - the generator's failure modes are opaque; a probe must not crash the build
        return None
