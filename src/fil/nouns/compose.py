"""A Quranic noun form → its composed {en, bs} gloss, or why it keeps its grammar label.

A form here is what a learner reads as one unit: the noun's word (بِأَيْدِيهِمْ, وَٱلْأَرْضِ)
together with the preposition standing alone before it, when there is one (فِي ٱلْأَرْضِ).
That preposition decides the Bosnian case ("na zemlji", "sa zemlje"), so a bare genitive
would have no single gloss without it.

The parts come from the corpus (fil.corpus.nouns): proclitics, article, possessor, case,
number. English is composed by rule (fil.nouns.english), Bosnian from the noun's stored
declension (fil.nouns.bosnian). Conservative, like the verbs' composer: a form is glossed
only when every place it stands in reads the same and nothing in it is beyond the rules —
and an accusative only where it is an object. After إِنَّ it is the subject, after كَانَ the
predicate, and some nouns are mostly adverbs in the accusative (يَوْمَ "on the day", حَقًّا
"truly"); those keep their label.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from fil.composition.decomposition import AND, SO
from fil.corpus.nouns import BI, KA, LI, OATH
from fil.nouns import bosnian, english
from fil.nouns.bosnian import BosnianNoun, CannotSay
from fil.nouns.english import EnglishNoun
from fil.nouns.catalogue import plural_kind, plural_pattern
from fil.nouns.model import (ACCUSATIVE, CONSTRUCT, DEFINITE, GENITIVE, NOMINATIVE, PLURAL, NounOccurrence,
                             NounParts)

# The corpus's lemma of a preposition standing alone → our name for it.
SEPARATE_PREPOSITIONS = {"فِي": "fi", "عَلَى": "ala", "مِن": "min", "إِلَى": "ila"}
_ATTACHED_PREPOSITIONS = {BI: "bi", LI: "li", KA: "ka"}
_CONJUNCTIONS = {AND: ("and", "i"), SO: ("so", "pa")}
_BOSNIAN_NUMBERS = {"S": bosnian.SINGULAR, "D": bosnian.DUAL, "P": bosnian.PLURAL}
_BOSNIAN_CASES = {NOMINATIVE: bosnian.NOMINATIVE, ACCUSATIVE: bosnian.ACCUSATIVE, GENITIVE: bosnian.GENITIVE}


@dataclass(frozen=True)
class NounGlossing:
    """What composing needs to know about one noun."""

    english: EnglishNoun
    bosnian: BosnianNoun
    is_accusative_adverbial: bool = False   # its bare accusative is mostly an adverb: يَوْمَ, حَقًّا
    lemma: str = ""
    is_polysemous: bool = False             # عَيْن "eye" or "spring", خَيْر "good" or "better": keep the labels
    main_plural: str | None = None          # the plural the Bosnian plural renders (عُيُون "springs" is not أَعْيُن "eyes")


@dataclass(frozen=True)
class Composed:
    en: str
    bs: str
    bosnian_case: str      # "L" — which case the Bosnian noun stands in


@dataclass(frozen=True)
class Skipped:
    reason: str


class BeyondTheRules(ValueError):
    """The form holds something the rules do not cover."""


def separate_preposition(occurrence: NounOccurrence) -> str | None:
    """The preposition standing alone before the word, as the corpus names it (فِي), or None."""
    parts = occurrence.parts
    if parts is None or parts.governing_preposition is None or _attached(parts):
        return None
    return parts.governing_preposition


def preposition_name(occurrence: NounOccurrence) -> str | None:
    """The preposition governing the noun, attached or standing before, by our name ("fi"), if
    it is one a gloss is composed for."""
    parts = occurrence.parts
    if parts is None:
        return None
    return _attached(parts) or SEPARATE_PREPOSITIONS.get(parts.governing_preposition or "")


def compose(occurrences: Sequence[NounOccurrence], noun: NounGlossing) -> Composed | Skipped:
    """The gloss of one form (all `occurrences` are of it), or the reason it keeps its label."""
    if noun.is_polysemous:
        return Skipped("polysemous noun")
    try:
        occurrence = single_reading(occurrences)
        return _composed(occurrence, noun)
    except (BeyondTheRules, CannotSay) as reason:
        return Skipped(str(reason))


def compose_one(occurrence: NounOccurrence, noun: NounGlossing) -> Composed | Skipped:
    return compose((occurrence,), noun)


def single_reading(occurrences: Sequence[NounOccurrence]) -> NounOccurrence:
    if not occurrences:
        raise BeyondTheRules("no occurrence")
    unclean = next((occurrence for occurrence in occurrences if not occurrence.is_clean), None)
    if unclean is not None:
        raise BeyondTheRules(unclean.skip_reason or "not decomposed")
    readings = {_reading(occurrence) for occurrence in occurrences}
    if len(readings) != 1:
        raise BeyondTheRules("readings differ")
    return occurrences[0]


def _reading(occurrence: NounOccurrence) -> tuple:
    parts = occurrence.parts
    return (occurrence.number, occurrence.case, occurrence.state, parts.proclitics, parts.has_article,
            parts.possessive, parts.governing_preposition, _follows(occurrence))


def _follows(occurrence: NounOccurrence) -> str | None:
    """What came before only matters to a bare accusative."""
    return occurrence.parts.follows if occurrence.case == ACCUSATIVE else None


def _composed(occurrence: NounOccurrence, noun: NounGlossing) -> Composed:
    parts = occurrence.parts
    if occurrence.case is None:
        raise BeyondTheRules("no case")
    _require_main_plural(occurrence, noun)
    conjunction = _conjunction(parts)
    is_oath = OATH in parts.proclitics
    preposition = None if is_oath else _preposition(occurrence)
    _require_object_if_accusative(occurrence, preposition, noun)
    wanted_bosnian = bosnian.Phrase(
        number=_BOSNIAN_NUMBERS[occurrence.number], case=_BOSNIAN_CASES[occurrence.case],
        preposition=preposition, possessor=parts.possessive, conjunction=conjunction[1], oath=is_oath)
    wanted_english = english.EnglishPhrase(
        number=occurrence.number, is_definite=occurrence.state == DEFINITE,
        is_construct=occurrence.state == CONSTRUCT, preposition=preposition,
        is_genitive=occurrence.case == GENITIVE and preposition is None and not is_oath,
        possessor=parts.possessive, conjunction=conjunction[0], oath=is_oath)
    return Composed(english.phrase(noun.english, wanted_english), bosnian.phrase(noun.bosnian, wanted_bosnian),
                    bosnian.case_of(noun.bosnian, wanted_bosnian))


def _require_main_plural(occurrence: NounOccurrence, noun: NounGlossing) -> None:
    """A second plural may mean something else (عُيُون "springs" beside أَعْيُن "eyes")."""
    if occurrence.number != PLURAL or noun.main_plural is None:
        return
    pattern = plural_pattern(plural_kind(noun.lemma, occurrence.stem), occurrence.stem)
    if pattern != plural_pattern(plural_kind(noun.lemma, noun.main_plural), noun.main_plural):
        raise BeyondTheRules("second plural")


def _conjunction(parts: NounParts) -> tuple[str | None, str | None]:
    others = [name for name in parts.proclitics if name not in (*_CONJUNCTIONS, *_ATTACHED_PREPOSITIONS, OATH)]
    if others:
        raise BeyondTheRules(f"proclitic {others[0]}")
    found = next((name for name in parts.proclitics if name in _CONJUNCTIONS), None)
    return _CONJUNCTIONS[found] if found else (None, None)


def _preposition(occurrence: NounOccurrence) -> str | None:
    parts = occurrence.parts
    attached = _attached(parts)
    if attached:
        return attached
    if parts.governing_preposition is None:
        return None
    name = SEPARATE_PREPOSITIONS.get(parts.governing_preposition)
    if name is None:
        raise BeyondTheRules(f"preposition {parts.governing_preposition}")
    return name


def _attached(parts: NounParts) -> str | None:
    return next((_ATTACHED_PREPOSITIONS[name] for name in parts.proclitics if name in _ATTACHED_PREPOSITIONS), None)


def _require_object_if_accusative(occurrence: NounOccurrence, preposition: str | None, noun: NounGlossing) -> None:
    if occurrence.case != ACCUSATIVE or preposition:
        return
    if occurrence.parts.follows:
        raise BeyondTheRules(f"accusative after {occurrence.parts.follows}")
    if noun.is_accusative_adverbial:
        raise BeyondTheRules("adverbial accusative")
