"""A Quranic form → its composed {en, bs} gloss, or the reason it keeps its grammar label.

Conservative by design: a form is composed only when every place it stands in splits the
same way, its letters read one way, and nothing in it is beyond the rules. Anything else
is skipped with a named reason — a grammar label is never wrong, a composed gloss can be.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass

from fil.attested_forms import AttestedForm
from fil.composition import bosnian, english
from fil.composition.decomposition import CannotCompose, Decomposition, decompose
from fil.composition.english import EnglishVerb
from fil.corpus.parse import Segment, VerbOccurrence

Reading = tuple[VerbOccurrence, Sequence[Segment]]   # one occurrence and the word it stands in

# A form seen once that carries this many parts besides its stem is too rare to trust a rule on.
RARE_MORPHEMES = 3

# Verbs whose meaning is not a plain action a rule can conjugate: لَيْسَ "is not", بِئْسَ "how
# wretched", عَسَىٰ "perhaps", كَادَ "almost", يَنْبَغِي "it befits", مَا زَالَ "still is"…
IDIOMATIC_VERBS = frozenset({"ليس|1", "بأس|1", "نعم|1", "عسي|1", "كود|1", "زيل|1", "بغي|7", "علو|6",
                             "سوأ|1", "هود|1", "قرر|1"})


@dataclass(frozen=True)
class Planned:
    """A form the rules understand: its single decomposition and its English."""

    decomposition: Decomposition
    english: str


@dataclass(frozen=True)
class Composed:
    en: str
    bs: str


@dataclass(frozen=True)
class Skipped:
    reason: str


def plan(verb: str, form: AttestedForm, readings: Sequence[Reading], meaning: str,
         polysemous: Collection[str] = frozenset()) -> Planned:
    """The form's decomposition and English, or CannotCompose naming why not.

    `polysemous` names verbs whose first sense is wrong in too many ayat (قَضَىٰ "decreed" where
    it is "fulfilled"): one sense for every form of them would mislead.
    """
    if verb in IDIOMATIC_VERBS:
        raise CannotCompose("idiomatic meaning")
    if verb in polysemous:
        raise CannotCompose("polysemous verb")
    if form.is_ambiguous:
        raise CannotCompose("ambiguous spelling")
    decomposition = _single_decomposition(readings)
    if _reads_as_you_or_she(decomposition):
        raise CannotCompose("you or she")
    if len(decomposition.cell.objects) > 1:
        raise CannotCompose("two objects")
    if _addresses_itself(decomposition):
        raise CannotCompose("object same as subject")
    if decomposition.cell.objects and decomposition.cell.is_passive:
        raise CannotCompose("passive with object")   # أُوتُوهُ: which object became the subject is unclear
    if form.count == 1 and decomposition.morpheme_count >= RARE_MORPHEMES:
        raise CannotCompose("rare and complex")
    return Planned(decomposition, english.gloss(decomposition, EnglishVerb.from_meaning(meaning)))


def compose(verb: str, form: AttestedForm, readings: Sequence[Reading], meaning: str,
            paradigm: Mapping[str, str], polysemous: Collection[str] = frozenset()) -> Composed | Skipped:
    """The form's gloss in English and Bosnian, or why it keeps its label (`verb` is "root|form")."""
    try:
        planned = plan(verb, form, readings, meaning, polysemous)
        proclitics, cell = planned.decomposition.proclitics, planned.decomposition.cell
        cell_text = bosnian.cell_text(proclitics, cell, paradigm)
        if cell_text is None:
            raise CannotCompose("no paradigm cell")
        return Composed(planned.english, bosnian.gloss(proclitics, cell, cell_text))
    except CannotCompose as reason:
        return Skipped(reason.reason)


# تَفْرَحُ is "you rejoice" and "she rejoices" alike, and the corpus does not always tell them
# apart (it tags لَا تَفْرَحْ in 28:76, said to Qārūn, as "she").
_YOU_OR_SHE = frozenset({"2MS", "3FS", "2D", "3FD"})


def _reads_as_you_or_she(decomposition: Decomposition) -> bool:
    cell = decomposition.cell
    return cell.tense in ("present", "future") and cell.subject in _YOU_OR_SHE


def _addresses_itself(decomposition: Decomposition) -> bool:
    """"(you two) come to you": Arabic does not take a first or second person as its own
    object, so such a split is the corpus's segmentation, not the Quran's meaning."""
    cell = decomposition.cell
    return any(found[0] == cell.subject[0] != "3" for found in cell.objects)


def _single_decomposition(readings: Sequence[Reading]) -> Decomposition:
    """Every place the form stands must split the same way (mood aside: it changes no gloss)."""
    found = {decompose(occurrence, word) for occurrence, word in readings}
    if len({(found_one.proclitics, found_one.cell) for found_one in found}) != 1:
        raise CannotCompose("readings differ")
    return min(found, key=lambda decomposition: decomposition.mood or "")
