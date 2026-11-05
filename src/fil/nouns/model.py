"""What a Quranic noun is: its occurrences, its lemma, and the cells of its paradigm.

Pure data. The vocabulary follows the corpus's own tags (NOM/ACC/GEN, S/D/P, M/F) so a
value read from the corpus needs no translation; the names for what the corpus leaves
implicit (definiteness, plural kinds, proclitic roles) are ours and spelled out here.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

# ------------------------------------------------------------------ kinds of lemma

NOUN = "noun"
ADJECTIVE = "adjective"
ACTIVE_PARTICIPLE = "active_participle"
PASSIVE_PARTICIPLE = "passive_participle"
VERBAL_NOUN = "verbal_noun"
ADVERB = "adverb"            # nouns of place and time used adverbially: عِندَ, بَيْنَ, يَوْمَئِذٍ
PROPER_NOUN = "proper_noun"
KINDS = (NOUN, ADJECTIVE, ACTIVE_PARTICIPLE, PASSIVE_PARTICIPLE, VERBAL_NOUN, ADVERB, PROPER_NOUN)

# ------------------------------------------------------------------ grammar

MASCULINE, FEMININE = "M", "F"
SINGULAR, DUAL, PLURAL = "S", "D", "P"
NUMBERS = (SINGULAR, DUAL, PLURAL)
NOMINATIVE, ACCUSATIVE, GENITIVE = "NOM", "ACC", "GEN"
CASES = (NOMINATIVE, ACCUSATIVE, GENITIVE)
DEFINITE = "definite"        # with the article: الْكِتَابُ
INDEFINITE = "indefinite"    # with nunation (or a diptote's bare ending): كِتَابٌ
CONSTRUCT = "construct"      # neither — possessed by a suffix or a following genitive: كِتَابُهُ
STATES = (DEFINITE, INDEFINITE)  # the two states a paradigm table shows

# The word families that change what an accusative does: after إِنَّ it is the subject
# ("إِنَّ ٱلْأَرْضَ" — the earth is…), after كَانَ the predicate. Neither is an object.
INNA, KANA = "inna", "kana"

# ------------------------------------------------------------------ plural kinds

SOUND_MASCULINE = "sound_masculine"   # مُؤْمِنُونَ
SOUND_FEMININE = "sound_feminine"     # ثَمَرَات
BROKEN = "broken"                     # أَيْدِي of يَد


@dataclass(frozen=True)
class NounParts:
    """A noun's word taken apart: what stands before the stem, what after, what governs it."""

    proclitics: tuple[str, ...]          # roles in order: "and", "question", "bi"… (never the article)
    has_article: bool
    possessive: str | None = None        # the possessor suffix as person-gender-number: "3MP"
    governing_preposition: str | None = None  # lemma of the preposition ruling a genitive: "ب", "فِي"
    follows: str | None = None           # the word before is إِنَّ or a sister (INNA), كَانَ or a sister (KANA)


@dataclass(frozen=True)
class NounOccurrence:
    """One noun (or adjective, participle, name) at one place in the Quran."""

    surah: int
    ayah: int
    word: int
    word_text: str               # the whole written word, clitics and all: بِأَيْدِيهِمْ
    stem: str                    # the noun alone: أَيْدِي
    lemma: str
    root: str
    kind: str                    # one of KINDS
    gender: str | None           # MASCULINE | FEMININE | None when the corpus leaves it open
    number: str                  # one of NUMBERS
    case: str | None             # one of CASES; None for the few words the corpus leaves uncased
    state: str                   # DEFINITE | INDEFINITE | CONSTRUCT
    verb_form: int | None        # a participle's or verbal noun's form (VF:n), else None
    parts: NounParts | None      # None when the word holds something beyond the rules…
    skip_reason: str | None = None  # …and this says what

    @property
    def is_clean(self) -> bool:
        return self.parts is not None

    @property
    def is_bare(self) -> bool:
        """Nothing around the stem but, perhaps, the article: a paradigm cell as written."""
        return self.parts is not None and not self.parts.proclitics and self.parts.possessive is None


@dataclass(frozen=True)
class AttestedNounForm:
    """One written word of a lemma, with how often and in which grammar it occurs."""

    text: str
    number: str
    case: str | None
    state: str
    count: int


@dataclass(frozen=True)
class PluralForm:
    text: str                    # the plural stem as the Quran most often writes it
    kind: str                    # SOUND_MASCULINE | SOUND_FEMININE | BROKEN
    count: int


@dataclass(frozen=True)
class NounLemma:
    """A dictionary entry: one lemma of one root, aggregated over the whole Quran."""

    lemma: str
    root: str
    kind: str
    gender: str | None
    count: int
    rank: int                    # 1 = most frequent; proper nouns are ranked among themselves
    verb_form: int | None
    plurals: tuple[PluralForm, ...]
    dual_count: int
    forms: tuple[AttestedNounForm, ...]   # most frequent first
    linked_verb: str | None      # our verb key ("كتب_1") when its root is one we teach
    numbers: tuple[str, ...] = (SINGULAR,)   # the rows of its case table, in NUMBERS order

    def forms_of(self, number: str) -> tuple[AttestedNounForm, ...]:
        return tuple(form for form in self.forms if form.number == number)


# ------------------------------------------------------------------ the paradigm

ATTESTED = "attested"
GENERATED = "generated"
MISSING = "missing"


@dataclass(frozen=True)
class Cell:
    number: str
    state: str
    case: str

    @property
    def code(self) -> str:
        return f"{self.number}|{self.state}|{self.case}"


@dataclass(frozen=True)
class ParadigmCell:
    cell: Cell
    text: str | None
    source: str                          # ATTESTED | GENERATED | MISSING
    problems: tuple[str, ...] = ()       # why a generated form was refused (then source is MISSING)


@dataclass(frozen=True)
class Paradigm:
    lemma: str
    root: str
    cells: tuple[ParadigmCell, ...]

    def text(self, number: str, state: str, case: str) -> str | None:
        return next((found.text for found in self.cells if found.cell == Cell(number, state, case)), None)

    def count(self, source: str) -> int:
        return sum(1 for found in self.cells if found.source == source)


def table_cells(numbers: Iterable[str]) -> tuple[Cell, ...]:
    """The definite × indefinite × NOM/ACC/GEN cells for each number, in reading order."""
    return tuple(Cell(number, state, case) for number in numbers for state in STATES for case in CASES)
