"""Composed glosses corrected in context: where a rule's gloss is wrong for the ayat its form stands in.

The rules gloss a form from its verb's first sense and its cell; the Quran sometimes uses the verb in
another sense there (أَخْرَجَ "drive out", not "bring out", 7:123), or its object is plainly a thing
(فَٱدْخُلُوهَا "enter it", not "enter her/it", 39:73). Such a form keeps its composed shape — the same
clitic words, the same command or question — with the sense its ayat need, and a reason.

Stored in data/composed_gloss_corrections.json as {"root|form|arabic": {"en", "bs", "why"}} and checked
against the rule's own gloss on every build: a correction of a form the rules no longer compose, or one
that changes the gloss's shape, fails the build rather than reaching a learner.

Where one form's ayat need different words — سَخَّرَهَا is "subjected it" of the sun and "subjected them"
of the winds — the correction is made per place instead, in data/composed_place_corrections.json as
{"root|form|arabic": {"surah:ayah:word": {"en", "bs", "why"}}}: the place shows its own gloss, the form's
row keeps the rule's. It is checked in the same way, against the rule's gloss at that place.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from fil.composition.bosnian import starts_with_enclitic

FIELDS = frozenset({"en", "bs", "why"})
# Bosnian in Latin script, as in the paradigms, with a closing "!" or "?".
_BOSNIAN = re.compile(r"^[a-zA-ZčćžšđČĆŽŠĐ' -]+[!?]?$")
# The words a proclitic puts in front: a correction keeps them ("so I broke my promise to you").
_LEADING_EN = ("and", "so", "surely", "so that", "let")
_LEADING_BS = ("i", "pa", "zaista", "da", "neka", "zar")


class InvalidCorrection(ValueError):
    """A correction that must not replace a composed gloss; the message names every problem."""


@dataclass(frozen=True)
class Correction:
    en: str
    bs: str
    why: str


def read(entries: Mapping[str, Mapping[str, str]]) -> dict[str, Correction]:
    """The stored corrections, or InvalidCorrection naming every malformed entry."""
    malformed = [f"{key}: fields {sorted(entry)}, not {sorted(FIELDS)}" for key, entry in entries.items()
                 if set(entry) != FIELDS or not all(str(value).strip() for value in entry.values())]
    if malformed:
        raise InvalidCorrection("; ".join(malformed))
    return {key: Correction(entry["en"], entry["bs"], entry["why"]) for key, entry in entries.items()}


def place_key(form: str, location: str) -> str:
    """How a correction of one place is named in lookups and messages: "سخر|2|سَخَّرَهَا 13:2:14"."""
    return f"{form} {location}"


def read_by_place(entries: Mapping[str, Mapping[str, Mapping[str, str]]]) -> dict[str, Correction]:
    """The stored per-place corrections by `place_key`, or InvalidCorrection naming every malformed entry."""
    return read({place_key(form, location): entry for form, by_location in entries.items()
                 for location, entry in by_location.items()})


def problems(key: str, correction: Correction, rule_en: str | None, rule_bs: str | None) -> list[str]:
    """Why `correction` may not replace the rule's gloss of the form `key` (None: the rules do not compose it)."""
    if rule_en is None or rule_bs is None:
        return [f"{key}: the rules no longer compose this form — drop or move the correction"]
    found = [f"{key}: {problem}" for problem in (
        *_shape_problems("en", correction.en, rule_en, _LEADING_EN),
        *_shape_problems("bs", correction.bs, rule_bs, _LEADING_BS),
        *_bosnian_problems(correction.bs),
    )]
    if (correction.en, correction.bs) == (rule_en, rule_bs):
        found.append(f"{key}: the same as the rule's gloss")
    return found


def validated(corrections: Mapping[str, Correction], composed: Mapping[str, tuple[str, str]]) -> dict[str, Correction]:
    """`corrections` checked against the rules' glosses (`composed`: key → (en, bs)), or InvalidCorrection."""
    found = [problem for key, correction in corrections.items()
             for problem in problems(key, correction, *composed.get(key, (None, None)))]
    if found:
        raise InvalidCorrection("; ".join(found))
    return dict(corrections)


def _shape_problems(language: str, corrected: str, rule: str, leading: tuple[str, ...]) -> list[str]:
    found = []
    if _ending(corrected) != _ending(rule):
        found.append(f"{language} {corrected!r} must end like the rule's {rule!r} (command \"!\", question \"?\")")
    if _leading(corrected, leading) != _leading(rule, leading):
        found.append(f"{language} {corrected!r} must open with the rule's clitic words, as {rule!r}")
    return found


def _bosnian_problems(text: str) -> list[str]:
    if not _BOSNIAN.match(text) or "  " in text:
        return [f"bs {text!r} is not plain Bosnian in Latin script"]
    if starts_with_enclitic(text):
        return [f"bs {text!r} opens with an enclitic"]
    return []


def _ending(text: str) -> str:
    return text[-1] if text.endswith(("!", "?")) else ""


def _leading(text: str, leading: tuple[str, ...]) -> str:
    """The longest clitic phrase the gloss opens with ("so that", not "so")."""
    return max((words for words in leading if text == words or text.startswith(words + " ")), key=len, default="")
