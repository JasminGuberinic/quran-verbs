"""A second, independent conjugator backed by CAMeL Tools (NYU Abu Dhabi).

Its whole purpose is to UNLOCK the consensus tier: when the Quran does not attest a
cell, a form that BOTH Qutrub and CAMeL produce is far more trustworthy than one
generator's guess. It is deliberately NOT in the default generator set — it loads a
~40 MB morphology database into memory — so a caller opts in by passing it explicitly.

CAMeL generates from a lemma + a feature bundle, so we (a) bridge our verb to CAMeL's
lemma by finding the lemma whose perfective 3ms reproduces our citation form, then
(b) generate each teachable cell. Orthographic differences from Qutrub are folded by
reconciliation, so this remains a genuine independent vote.
"""

from __future__ import annotations

from functools import cached_property

from fil.conjugation import ConjugationTable
from fil.models import Verb
from fil.reconciliation import forms_match

_DB = "calima-msa-r13"

# our tense key → CAMeL aspect/mood features
_TENSE_FEATS = {
    "past": {"asp": "p", "mod": "i"},
    "present": {"asp": "i", "mod": "i"},
    "imperative": {"asp": "c"},
}

# our pronoun key → CAMeL person/gender/number (duals default to masculine)
_PGN = {
    "ana": {"per": "1", "gen": "m", "num": "s"},
    "nahnu": {"per": "1", "gen": "m", "num": "p"},
    "anta": {"per": "2", "gen": "m", "num": "s"},
    "anti": {"per": "2", "gen": "f", "num": "s"},
    "antuma": {"per": "2", "gen": "m", "num": "d"},
    "antum": {"per": "2", "gen": "m", "num": "p"},
    "antunna": {"per": "2", "gen": "f", "num": "p"},
    "huwa": {"per": "3", "gen": "m", "num": "s"},
    "hiya": {"per": "3", "gen": "f", "num": "s"},
    "huma": {"per": "3", "gen": "m", "num": "d"},
    "hum": {"per": "3", "gen": "m", "num": "p"},
    "hunna": {"per": "3", "gen": "f", "num": "p"},
}

_PERF_3MS = {"asp": "p", "per": "3", "gen": "m", "num": "s", "mod": "i"}


class CamelConjugator:
    """Conjugator backed by CAMeL Tools' MSA morphology database."""

    @cached_property
    def _analyzer(self):
        from camel_tools.morphology.analyzer import Analyzer
        from camel_tools.morphology.database import MorphologyDB

        return Analyzer(MorphologyDB.builtin_db(_DB, "a"))

    @cached_property
    def _generator(self):
        from camel_tools.morphology.database import MorphologyDB
        from camel_tools.morphology.generator import Generator

        return Generator(MorphologyDB.builtin_db(_DB, "g"))

    def conjugate(self, verb: Verb) -> ConjugationTable:
        lemma = self._lemma_for(verb)
        if lemma is None:
            return {}  # can't bridge this verb → contribute no vote (safe)
        table: ConjugationTable = {}
        for tense, tense_feats in _TENSE_FEATS.items():
            cells = self._tense(lemma, tense_feats)
            if cells:
                table[tense] = cells
        return table

    def _tense(self, lemma: str, tense_feats: dict[str, str]) -> dict[str, str]:
        cells: dict[str, str] = {}
        for pronoun, pgn in _PGN.items():
            form = self._one(lemma, {"pos": "verb", "vox": "a", **tense_feats, **pgn})
            if form:
                cells[pronoun] = form
        return cells

    def _lemma_for(self, verb: Verb) -> str | None:
        """The CAMeL lemma whose perfective 3ms reproduces our citation form."""
        for lemma in self._verb_lemmas(verb.past3ms):
            produced = self._one(lemma, {"pos": "verb", "vox": "a", **_PERF_3MS})
            if produced and forms_match(produced, verb.past3ms):
                return lemma
        return None

    def _verb_lemmas(self, surface: str) -> list[str]:
        seen: list[str] = []
        for analysis in self._analyzer.analyze(surface):
            if analysis.get("pos") == "verb" and analysis["lex"] not in seen:
                seen.append(analysis["lex"])
        return seen

    def _one(self, lemma: str, feats: dict[str, str]) -> str | None:
        try:
            produced = self._generator.generate(lemma, feats)
        except Exception:  # noqa: BLE001 - CAMeL raises on many feature combos; skip the cell
            return None
        forms = sorted({analysis["diac"] for analysis in produced if analysis.get("diac")})
        return forms[0] if forms else None
