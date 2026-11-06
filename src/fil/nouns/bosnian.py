"""A noun in Bosnian: its declension, written once, and the phrases built from it.

Bosnian declension is too irregular for rules (ruka → ruci, dan → dana, ljudi → ljudima),
so each noun carries the cells a gloss needs — seven cases are six here, the vocative is
never needed — written once by a model and validated on import (`validated`). Everything
around the noun is regular and done by rule:

  - the case a preposition takes: "u"/"na"/"o" the locative, "iz"/"od"/"do" the genitive,
    "prema"/"k" the dative, "s" the instrumental, "za" the accusative, "kao" the nominative;
  - "s"/"sa" and "k"/"ka" by the word that follows ("sa sinom", "s rukom");
  - the possessive adjective, which agrees with the noun in gender, number and case
    ("u njegovoj ruci", "s njihovim rukama", "njegov narod");
  - the order: conjunction, preposition, possessive, noun.

Which Bosnian preposition renders an Arabic one depends on the noun (فِي ٱلْأَرْضِ is "na
zemlji", فِي ٱلْبَيْتِ "u kući"), so that choice is stored with the noun too.

Pure: data in, text out.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

# ------------------------------------------------------------------ the noun's own cells

SINGULAR, DUAL, PLURAL = "sg", "du", "pl"
NUMBERS = (SINGULAR, DUAL, PLURAL)
NOMINATIVE, GENITIVE, DATIVE, ACCUSATIVE, INSTRUMENTAL, LOCATIVE = "N", "G", "D", "A", "I", "L"
CASES = (NOMINATIVE, GENITIVE, DATIVE, ACCUSATIVE, INSTRUMENTAL, LOCATIVE)
CASE_NAMES = {NOMINATIVE: "nominativ", GENITIVE: "genitiv", DATIVE: "dativ", ACCUSATIVE: "akuzativ",
              INSTRUMENTAL: "instrumental", LOCATIVE: "lokativ"}

MASCULINE, MASCULINE_ANIMATE, FEMININE, NEUTER = "m", "ma", "f", "n"
GENDERS = (MASCULINE, MASCULINE_ANIMATE, FEMININE, NEUTER)

# ------------------------------------------------------------------ prepositions

# The Arabic prepositions a gloss is composed for, by the names fil.nouns.compose uses,
# and the Bosnian prepositions each may be rendered by ("" = the bare case).
ARABIC_PREPOSITIONS: Mapping[str, tuple[str, ...]] = {
    "fi": ("u", "na"),            # فِي
    "ala": ("na",),               # عَلَى
    "bi": ("", "s"),              # بِـ  instrumental: "rukom" / "s narodom"
    "min": ("iz", "od"),          # مِنْ
    "ila": ("do", "prema", "k"),  # إِلَى
    "li": ("", "za"),             # لِـ  dative: "ljudima" / "za ljude"
    "ka": ("kao",),               # كَـ
}
NOT_COMPOSED = "-"   # any preposition may be left uncomposed for a noun: كَذَّبُوا بِآيَاتِنَا is "naše znakove"
                     # after the verb, not "našim znacima" — the case follows the verb, which a form does not see
DEFAULT_CASE = {"bi": INSTRUMENTAL, "li": DATIVE}   # the bare case of a preposition rendered by none
_CASE_OF = {"u": LOCATIVE, "na": LOCATIVE, "o": LOCATIVE, "iz": GENITIVE, "od": GENITIVE, "do": GENITIVE,
            "prema": DATIVE, "k": DATIVE, "s": INSTRUMENTAL, "za": ACCUSATIVE, "kao": NOMINATIVE}
_SA_BEFORE = ("s", "š", "z", "ž")     # "sa sinom", "sa zemlje" — "s" elsewhere
_KA_BEFORE = ("k", "g", "h")          # "ka kući" — "k" elsewhere

# ------------------------------------------------------------------ possessive adjectives

# The possessor (person, gender, number, as the corpus writes it) → the adjective's stem.
POSSESSORS: Mapping[str, str] = {
    "1S": "moj", "1P": "naš",
    "2MS": "tvoj", "2FS": "tvoj", "2MP": "vaš", "2FP": "vaš", "2D": "vaš",
    "3MS": "njegov", "3FS": "njen", "3MP": "njihov", "3FP": "njihov", "3D": "njihov", "3MD": "njihov", "3FD": "njihov",
}
# Endings by gender (m, n, f) × number × case, for the hard stems njegov, njen, njihov.
_HARD = {
    (MASCULINE, SINGULAR): ("", "og", "om", "", "im", "om"),
    (NEUTER, SINGULAR): ("o", "og", "om", "o", "im", "om"),
    (FEMININE, SINGULAR): ("a", "e", "oj", "u", "om", "oj"),
    (MASCULINE, PLURAL): ("i", "ih", "im", "e", "im", "im"),
    (NEUTER, PLURAL): ("a", "ih", "im", "a", "im", "im"),
    (FEMININE, PLURAL): ("e", "ih", "im", "e", "im", "im"),
}
# naš, vaš: soft stems — "našeg", "našem", "naše".
_SOFT = {**_HARD,
         (MASCULINE, SINGULAR): ("", "eg", "em", "", "im", "em"),
         (NEUTER, SINGULAR): ("e", "eg", "em", "e", "im", "em")}
# moj, tvoj: soft, and short in the masculine and neuter singular — "mog", "mom".
_SHORT = {"moj": "m", "tvoj": "tv"}
_SHORT_ENDINGS = {GENITIVE: "og", DATIVE: "om", LOCATIVE: "om"}

_BOSNIAN = re.compile(r"^[a-zA-ZčćžšđČĆŽŠĐ' -]+$")
PLURAL_FORMS = "pluralForms"   # entry key: the numbers declined as Bosnian plurals (a collective's "sg": deve)
SINGULAR_FORMS = "singularForms"   # entry key: the numbers whose Bosnian word is a collective singular (djeca)
CELL = re.compile(r"^(sg|du|pl)\|(N|G|D|A|I|L)$")


class InvalidBosnianNoun(ValueError):
    """A stored declension that must not become a gloss; the message names every problem."""


@dataclass(frozen=True)
class BosnianNoun:
    """A noun's Bosnian cells ("sg|L" → "ruci"), the gender of each number, and its prepositions."""

    cells: Mapping[str, str]
    genders: Mapping[str, str]          # "sg" → "f"; "ma" is a masculine animate (its A is its G)
    prepositions: Mapping[str, str]     # "fi" → "na"
    # The numbers whose Bosnian words are plurals: a collective's own row (إِبِل → "deve"),
    # so what agrees with it is plural too ("njegove deve", never "njegova deve").
    plural_numbers: frozenset[str] = frozenset()
    # The numbers whose Bosnian word is a collective singular in form — djeca, braća, odjeća
    # for an Arabic plural — so what agrees with it is feminine singular ("njihova djeca",
    # "njihovoj djeci"), never plural ("njihove djeca").
    singular_numbers: frozenset[str] = frozenset()

    def cell(self, number: str, case: str) -> str | None:
        return self.cells.get(f"{number}|{case}")

    def agreement(self, number: str) -> tuple[str, str] | None:
        """The gender and Bosnian number of what agrees with this number's word, if it has a gender."""
        gender = self.genders.get(number)
        if gender is None:
            return None
        if number in self.singular_numbers:
            return FEMININE, SINGULAR
        return gender, PLURAL if number in self.plural_numbers else number


@dataclass(frozen=True)
class Phrase:
    """What stands around the noun: its conjunction, preposition and possessor."""

    number: str = SINGULAR
    case: str = NOMINATIVE               # the Bosnian case when no preposition decides it
    preposition: str | None = None       # an ARABIC_PREPOSITIONS name
    possessor: str | None = None         # "3MP"
    conjunction: str | None = None       # "i", "pa"
    oath: bool = False                   # "tako mi" + genitive: وَٱلشَّمْسِ "tako mi sunca"


class CannotSay(ValueError):
    """The noun lacks what this phrase needs (a cell, a gender, a preposition choice)."""


def phrase(noun: BosnianNoun, wanted: Phrase) -> str:
    """The phrase in Bosnian: "i u njegovoj ruci"."""
    preposition, case = _preposition_and_case(noun, wanted)
    text = noun.cell(wanted.number, case)
    if text is None:
        raise CannotSay(f"no {wanted.number}|{case} cell")
    words = [_possessive(noun, wanted.possessor, wanted.number, case), text] if wanted.possessor else [text]
    if wanted.oath:
        words = ["tako", "mi", *words]
    if preposition:
        words = [_euphonic(preposition, words[0]), *words]
    if wanted.conjunction:
        words = [wanted.conjunction, *words]
    return " ".join(words)


def case_of(noun: BosnianNoun, wanted: Phrase) -> str:
    """The Bosnian case the noun stands in for this phrase."""
    return _preposition_and_case(noun, wanted)[1]


def _preposition_and_case(noun: BosnianNoun, wanted: Phrase) -> tuple[str, str]:
    if wanted.oath:
        return "", GENITIVE
    if wanted.preposition is None:
        return "", wanted.case
    chosen = noun.prepositions.get(wanted.preposition)
    if chosen is None:
        raise CannotSay(f"no Bosnian preposition chosen for {wanted.preposition}")
    if chosen == NOT_COMPOSED:
        raise CannotSay(f"{wanted.preposition} not composed for this noun")
    return chosen, _CASE_OF.get(chosen) or DEFAULT_CASE[wanted.preposition]


def _euphonic(preposition: str, following: str) -> str:
    first = following[:1].lower()
    if preposition == "s":
        return "sa" if first in _SA_BEFORE or following.lower().startswith("mn") else "s"
    if preposition == "k":
        return "ka" if first in _KA_BEFORE else "k"
    return preposition


def possessive_adjective(possessor: str, gender: str, number: str, case: str) -> str:
    """"njegovoj" — the possessor's adjective agreeing with a noun of this gender, number and case."""
    stem = POSSESSORS.get(possessor)
    if stem is None:
        raise CannotSay(f"unknown possessor {possessor}")
    is_animate = gender == MASCULINE_ANIMATE
    agreement = MASCULINE if is_animate else gender
    row = PLURAL if number == PLURAL else SINGULAR
    if is_animate and row == SINGULAR and case == ACCUSATIVE:
        case = GENITIVE      # "vidim njegovog sina", but "vidim njegov grad"
    if stem in _SHORT and agreement != FEMININE and row == SINGULAR and case in _SHORT_ENDINGS:
        return _SHORT[stem] + _SHORT_ENDINGS[case]
    endings = (_SOFT if stem.endswith(("š", "j")) else _HARD)[(agreement, row)]
    return stem + endings[CASES.index(case)]


def _possessive(noun: BosnianNoun, possessor: str, number: str, case: str) -> str:
    if number == DUAL:
        raise CannotSay("a possessed dual")
    agreement = noun.agreement(number)
    if agreement is None:
        raise CannotSay(f"no gender for {number}")
    gender, agreeing_number = agreement
    return possessive_adjective(possessor, gender, agreeing_number, case)


# ------------------------------------------------------------------ validation on import

def validated(entries: Mapping[str, Mapping], needs: Mapping[str, tuple[str, ...]]) -> dict[str, BosnianNoun]:
    """Stored declensions → nouns, or InvalidBosnianNoun naming every problem.

    `needs` gives, per noun key, the numbers it must have cells for ("sg", "pl", "du").
    """
    problems = [problem for key, entry in entries.items() for problem in _problems(key, entry, needs.get(key, ()))]
    if problems:
        raise InvalidBosnianNoun("; ".join(problems))
    return {key: from_entry(entry) for key, entry in entries.items()}


def from_entry(entry: Mapping) -> BosnianNoun:
    return BosnianNoun(cells=dict(entry["cells"]), genders=dict(entry["genders"]),
                       prepositions=dict(entry["prepositions"]), plural_numbers=frozenset(entry.get(PLURAL_FORMS, ())),
                       singular_numbers=frozenset(entry.get(SINGULAR_FORMS, ())))


def _problems(key: str, entry: Mapping, numbers: tuple[str, ...]) -> list[str]:
    if not isinstance(entry, Mapping) or not {"cells", "genders", "prepositions"} <= set(entry):
        return [f"{key}: needs cells, genders and prepositions"]
    found = [*_cell_problems(key, entry["cells"]), *_gender_problems(key, entry["genders"]),
             *_preposition_problems(key, entry["prepositions"]),
             *(f"{key}: {listing} lists {number!r}, not a number" for listing in (PLURAL_FORMS, SINGULAR_FORMS)
               for number in entry.get(listing, ()) if number not in NUMBERS)]
    missing = [f"{number}|{case}" for number in numbers for case in CASES if f"{number}|{case}" not in entry["cells"]]
    if missing:
        found.append(f"{key}: missing {', '.join(missing)}")
    return found


def _cell_problems(key: str, cells: Mapping[str, str]) -> list[str]:
    return [f"{key} {code}: " + ("no such cell" if not CELL.match(code) else f"not plain Bosnian: {text!r}")
            for code, text in cells.items()
            if not CELL.match(code) or not isinstance(text, str) or not _BOSNIAN.match(text) or "  " in text]


def _gender_problems(key: str, genders: Mapping[str, str]) -> list[str]:
    return [f"{key}: gender of {number} must be one of {'/'.join(GENDERS)}, not {gender!r}"
            for number, gender in genders.items() if number not in NUMBERS or gender not in GENDERS]


def _preposition_problems(key: str, prepositions: Mapping[str, str]) -> list[str]:
    wrong = [f"{key}: {name} → {chosen!r} (allowed: {', '.join(repr(option) for option in ARABIC_PREPOSITIONS.get(name, ()))})"
             for name, chosen in prepositions.items()
             if name not in ARABIC_PREPOSITIONS or chosen not in (*ARABIC_PREPOSITIONS[name], NOT_COMPOSED)]
    missing = [name for name in ARABIC_PREPOSITIONS if name not in prepositions]
    return wrong + ([f"{key}: no choice for {', '.join(missing)}"] if missing else [])
