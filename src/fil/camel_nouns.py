"""CAMeL Tools as a noun generator: the `NounGenerator` port's adapter.

CAMeL declines a lemma ("lex") for number, state and case. Two bridges are needed:
our corpus lemma to CAMeL's lex (the same word, found by analysing the lemma and keeping
the noun/adjective analyses whose lex is spelled like it), and our cell to CAMeL's
features. Participles and adjectives exist in both genders under one lex, so the
lemma's gender is passed when the corpus knows it.

Two habits of CAMeL's spelling are mended here, at the edge. It writes the underlying
case vowel on the final yāʾ of a defective noun (الأَيْدِيُ), which Arabic never writes —
the yāʾ is silent in the nominative and genitive (الْأَيْدِي); the gate would refuse it.
And it leaves the article bare (السَعْيُ, الكِتابُ), where a learner reads the sun letter
doubled and the lām of a moon letter silent: السَّعْيُ, الْكِتابُ.
"""

from __future__ import annotations

import unicodedata
from functools import cached_property

from fil.camel import _DB
from fil.nouns.model import DEFINITE, FEMININE, MASCULINE, Cell, NounLemma
from fil.nouns.spelling import skeleton, spelling_key

_NUMBERS = {"S": "s", "D": "d", "P": "p"}
_CASES = {"NOM": "n", "ACC": "a", "GEN": "g"}
_GENDERS = {MASCULINE: "m", FEMININE: "f"}
_POS = ("noun", "adj", "noun_quant", "noun_num", "adj_comp", "noun_prop")   # noun_prop: CAMeL files آيَة only so
_KASRA, _DAMMA = chr(0x0650), chr(0x064F)
_DEFECTIVE_ENDINGS = (_KASRA + "ي" + _DAMMA, _KASRA + "ي" + _KASRA)
_SHADDA, _SUKUN = chr(0x0651), chr(0x0652)
_SUN_LETTERS = set("تثدذرزسشصضطظلن")


class CamelNounGenerator:
    """Implements fil.nouns.paradigm.NounGenerator with CAMeL's MSA database."""

    is_heavy = True

    @cached_property
    def _database(self):
        from camel_tools.morphology.database import MorphologyDB

        return MorphologyDB.builtin_db(_DB, "ag")

    @cached_property
    def _analyzer(self):
        from camel_tools.morphology.analyzer import Analyzer

        return Analyzer(self._database)

    @cached_property
    def _generator(self):
        from camel_tools.morphology.generator import Generator

        return Generator(self._database)

    def __init__(self, is_gender_strict: bool = False) -> None:
        """`is_gender_strict`: never fall back to an ungendered request. A noun's gender is a
        hint (CAMeL files some nouns without one); an adjective's is the cell asked for — asked
        for a masculine plural it does not know, CAMeL would answer with the feminine one."""
        self._lexemes: dict[str, tuple[tuple[str, str], ...]] = {}
        self._is_gender_strict = is_gender_strict

    def generate(self, lemma: NounLemma, cell: Cell) -> tuple[str, ...]:
        """Every form CAMeL gives for the cell, trying each part of speech the lex has."""
        for lex, pos in self.lexemes(lemma.lemma):
            forms = self._declined(lex, pos, lemma, cell)
            if forms:
                return tuple(dict.fromkeys(_with_voweled_article(_without_defective_vowel(form)) for form in forms))
        return ()

    def lexemes(self, lemma: str) -> tuple[tuple[str, str], ...]:
        """(lex, part of speech) of the one CAMeL lex that is our lemma; empty when there is
        none, or when several distinct lexes claim it and we cannot tell which."""
        if lemma not in self._lexemes:
            found = self._candidates(lemma)
            is_one_word = len({lex for lex, _pos in found}) == 1
            self._lexemes[lemma] = tuple(sorted(found, key=lambda item: item[1] != "noun")) if is_one_word else ()
        return self._lexemes[lemma]

    def _candidates(self, lemma: str) -> list[tuple[str, str]]:
        analyses = self._analyzer.analyze(lemma)
        candidates = list(dict.fromkeys((analysis["lex"], analysis["pos"]) for analysis in analyses
                                        if analysis.get("pos") in _POS))
        exact = [found for found in candidates if spelling_key(found[0]) == spelling_key(lemma)]
        same_letters = [found for found in candidates if skeleton(found[0]) == skeleton(lemma)]
        return exact or same_letters

    def _declined(self, lex: str, pos: str, lemma: NounLemma, cell: Cell) -> tuple[str, ...]:
        features = {"pos": pos, "num": _NUMBERS[cell.number], "cas": _CASES[cell.case], **_state(cell)}
        if lemma.gender in _GENDERS:
            gendered = self._forms(lex, {**features, "gen": _GENDERS[lemma.gender]})
            return gendered if gendered or self._is_gender_strict else self._forms(lex, features)
        return self._forms(lex, features)

    def _forms(self, lex: str, features: dict[str, str]) -> tuple[str, ...]:
        try:
            produced = self._generator.generate(lex, features)
        except Exception:  # noqa: BLE001 - CAMeL raises on feature bundles a lex does not take
            return ()
        return tuple(sorted({analysis["diac"] for analysis in produced if analysis.get("diac")}))


def _state(cell: Cell) -> dict[str, str]:
    return {"stt": "d", "prc0": "Al_det"} if cell.state == DEFINITE else {"stt": "i"}


def _without_defective_vowel(form: str) -> str:
    return form[:-1] if form.endswith(_DEFECTIVE_ENDINGS) else form


def _with_voweled_article(form: str) -> str:
    if not form.startswith("ال") or len(form) < 3 or unicodedata.combining(form[2]):
        return form
    letter = form[2]
    if letter in _SUN_LETTERS:
        return form if form[3:4] == _SHADDA else form[:3] + _SHADDA + form[3:]
    return form[:2] + _SUKUN + form[2:]
