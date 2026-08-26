"""Generate a full, vocalized conjugation table for a Verb.

A `Conjugator` is a strategy that turns a Verb into a conjugation table. Having a
port (rather than one hard-wired tool) is what lets the engine run several
INDEPENDENT generators and cross-check them: when the Quran does not attest a cell,
two generators agreeing is far stronger evidence than trusting one blindly (see the
consensus tier in reconciliation).

`QutrubConjugator` is the first adapter — it wraps libqutrub, a mature rule-based
Arabic conjugator that outputs full tashkīl. We expose exactly the tenses and
pronouns we teach, as clean lowercase keys, so the rest of the pipeline never
touches a generator's Arabic internals.
"""

from __future__ import annotations

from typing import Protocol

from libqutrub.classverb import DAMMA, FATHA, KASRA, VerbClass
import libqutrub.verb_const as qutrub

from fil.models import Verb
from fil.vocalization import has_vocalized_ending, with_pausal_sukun

# {tense: {pronoun_key: vocalized_form}} — the shape every conjugator returns.
ConjugationTable = dict[str, dict[str, str]]


class Conjugator(Protocol):
    """A strategy that produces a verb's teachable conjugation table.

    A generator declares its own cost through `is_heavy`, so a caller planning a large run
    can be refused before it starts rather than after it has eaten the machine's memory
    (see fil.governor). Cheap is the default; only a generator that loads a database says
    otherwise.
    """

    is_heavy: bool

    def conjugate(self, verb: Verb) -> ConjugationTable: ...


# The present-tense stem vowel the author gives us, mapped to Qutrub's constant.
_PRESENT_VOWEL = {"a": FATHA, "i": KASRA, "u": DAMMA}

# The three tenses we teach, as clean keys → Qutrub's (Arabic) tense names.
_TENSES = {
    "past": qutrub.TensePast,          # الماضي
    "present": qutrub.TenseFuture,     # المضارع
    "imperative": qutrub.TenseImperative,  # الأمر
}

# The pronouns we teach, in teaching order: clean key → Qutrub's pronoun.
# (Imperative only has 2nd-person cells; empty results are dropped below.)
_PRONOUNS = [
    ("ana", qutrub.PronounAna),        # أنا   I
    ("nahnu", qutrub.PronounNahnu),    # نحن   we
    ("anta", qutrub.PronounAnta),      # أنتَ  you (m.)
    ("anti", qutrub.PronounAnti),      # أنتِ  you (f.)
    ("antuma", qutrub.PronounAntuma),  # أنتما you (dual)
    ("antum", qutrub.PronounAntum),    # أنتم  you (m. pl.)
    ("antunna", qutrub.PronounAntunna),  # أنتن you (f. pl.)
    ("huwa", qutrub.PronounHuwa),      # هو    he
    ("hiya", qutrub.PronounHya),       # هي    she
    ("huma", qutrub.PronounHuma),      # هما   they (dual)
    ("hum", qutrub.PronounHum),        # هم    they (m.)
    ("hunna", qutrub.PronounHunna),    # هن    they (f.)
]


class QutrubConjugator:
    """Conjugator backed by libqutrub — a mature rule-based Arabic conjugator."""

    is_heavy = False  # pure rules, no database to load

    def conjugate(self, verb: Verb) -> ConjugationTable:
        """Return {tense: {pronoun_key: vocalized_form}} for the teachable cells.

        Cells that do not exist for a tense (e.g. a 1st-person imperative) are
        simply absent, so the table only ever contains real forms.
        """
        engine = VerbClass(verb.past3ms, verb.transitive, _PRESENT_VOWEL[verb.present_vowel])
        engine.conjugate_all_tenses()
        return {tense: self._tense(engine, name) for tense, name in _TENSES.items()}

    def _tense(self, engine: VerbClass, tense_name: str) -> dict[str, str]:
        """Conjugate one tense across every pronoun, dropping empty cells.

        Each form is completed with its pausal sukūn (the generator sometimes
        leaves a bare final consonant) and then asserted to be fully vocalized —
        a form that still lacks a vocalized ending is a defect we refuse to emit.
        """
        cells: dict[str, str] = {}
        for pronoun_key, pronoun_name in _PRONOUNS:
            raw = engine.get_conj(tense_name, pronoun_name)
            if not (raw and raw.strip()):
                continue
            form = with_pausal_sukun(raw.strip())
            if not has_vocalized_ending(form):
                raise ValueError(
                    f"form '{form}' has an unvocalized ending ({tense_name}/{pronoun_key})"
                )
            cells[pronoun_key] = form
        return cells


# The default generator the rest of the pipeline uses today.
_DEFAULT: Conjugator = QutrubConjugator()


def conjugate(verb: Verb) -> ConjugationTable:
    """Conjugate a verb with the default (Qutrub) generator."""
    return _DEFAULT.conjugate(verb)
