"""A Quranic form of an adjective → its composed {en, bs} gloss, or why it keeps its label.

An adjective's case is its noun's, and the Bosnian case of that noun is decided by what
governs the noun — which the adjective's own word does not show (عَذَابٌ أَلِيمٌ, بِعَذَابٍ
أَلِيمٍ). So the gloss gives what the form does say: the article, a conjunction, and the
adjective in the Bosnian gender and number of the Arabic form, in the nominative ("i bolna",
"the painful"); the page shows its case beside it. A form that holds more than that — a
preposition or possessor (it is then used as a noun: مِنَ ٱلصَّٰبِرِينَ), a dual, a reading that
differs between places — keeps its grammar label, as the nouns' composer does (fil.nouns.compose).

Pure.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from fil.adjectives import bosnian, english
from fil.composition.decomposition import AND, SO
from fil.nouns import bosnian as bosnian_nouns
from fil.nouns.compose import BeyondTheRules, Composed, Skipped, single_reading
from fil.nouns.model import DEFINITE, FEMININE, MASCULINE, PLURAL, SINGULAR, NounOccurrence

_CONJUNCTIONS = {AND: ("and", "i"), SO: ("so", "pa")}
_GENDERS = {MASCULINE: bosnian_nouns.MASCULINE, FEMININE: bosnian_nouns.FEMININE}
_NUMBERS = {SINGULAR: bosnian_nouns.SINGULAR, PLURAL: bosnian_nouns.PLURAL}


@dataclass(frozen=True)
class AdjectiveGlossing:
    en: str          # "painful" — the first English sense
    bs_long: str     # "bolni" — the long masculine nominative
    bs_short: str    # "bolan" — the short form, for an indefinite masculine singular


def compose(occurrences: Sequence[NounOccurrence], adjective: AdjectiveGlossing) -> Composed | Skipped:
    try:
        occurrence = single_reading(occurrences)
        return _composed(occurrence, adjective)
    except BeyondTheRules as reason:
        return Skipped(str(reason))


def _composed(occurrence: NounOccurrence, adjective: AdjectiveGlossing) -> Composed:
    parts = occurrence.parts
    if occurrence.case is None or occurrence.gender not in _GENDERS or occurrence.number not in _NUMBERS:
        raise BeyondTheRules("no single gender, number and case")
    if parts.possessive or parts.governing_preposition:
        raise BeyondTheRules("used as a noun")
    others = [name for name in parts.proclitics if name not in _CONJUNCTIONS]
    if others:
        raise BeyondTheRules(f"proclitic {others[0]}")
    conjunction = next((_CONJUNCTIONS[name] for name in parts.proclitics if name in _CONJUNCTIONS), (None, None))
    bosnian_word = bosnian.attribute(adjective.bs_long, _GENDERS[occurrence.gender], _NUMBERS[occurrence.number],
                                     short_form=adjective.bs_short, is_definite=occurrence.state == DEFINITE)
    return Composed(english.phrase(adjective.en, occurrence.state == DEFINITE, conjunction[0]),
                    " ".join(word for word in (conjunction[1], bosnian_word) if word), bosnian_nouns.NOMINATIVE)
