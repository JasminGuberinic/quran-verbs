"""Polysemous verbs composed ayah by ayah: each place a form stands takes the sense its ayah needs.

قَضَىٰ is "decreed" in one ayah and "fulfilled" in another: no one sense fits every form of the verb,
so the rules never gloss such a form from its verb's first sense (fil.composition.compose). Instead
each verb lists its senses (data/polysemous_verbs.json, the first being the verb's own first sense) and
each ayah a form stands in is given one of them, with a reason (data/polysemous_sense_choices.json).
English is conjugated from the chosen sense; Bosnian comes from that sense's own paradigm,
"root|form@sense" in data/bs_paradigms.json (the first sense keeps the verb's paradigm, "root|form").

A choice names a form and a place it stands; one that no longer does — the form glossed by hand, the
place gone from the corpus, the sense gone from the list — is stale, and fails the build.

Pure: the stored entries in, validated senses and choices out.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping
from dataclasses import dataclass

from fil.composition.decomposition import CannotCompose
from fil.composition.english import EnglishVerb

SENSE_SEPARATOR = "@"     # "قضي|1@fulfil": the paradigm of a verb's other sense
_SENSE_ID = re.compile(r"^[a-z]+(-[a-z]+)*$")
_LOCATION = re.compile(r"^\d+:\d+:\d+$")
CHOICE_FIELDS = frozenset({"sense", "why"})


class InvalidSenses(ValueError):
    """A sense list or a sense choice that must not gloss a form; the message names every problem."""


@dataclass(frozen=True)
class Sense:
    id: str           # a short English name: "fulfil", "accept-repentance"
    en: str           # a plain "to …" meaning the English rules conjugate
    bs: str           # the Bosnian infinitive, a hint for whoever writes the sense's paradigm


@dataclass(frozen=True)
class PolysemousVerb:
    key: str                       # "root|form"
    senses: tuple[Sense, ...]      # the first is the verb's own first sense

    def sense(self, sense_id: str) -> Sense:
        return next(sense for sense in self.senses if sense.id == sense_id)

    def has_sense(self, sense_id: str) -> bool:
        return any(sense.id == sense_id for sense in self.senses)

    def paradigm_key(self, sense_id: str) -> str:
        """The first sense is the verb's own and keeps its paradigm; another has one of its own."""
        return self.key if sense_id == self.senses[0].id else f"{self.key}{SENSE_SEPARATOR}{sense_id}"


@dataclass(frozen=True)
class SenseChoice:
    sense: str
    why: str


# form key ("root|form|arabic") → location key ("2:117:5") → the sense chosen there
Choices = Mapping[str, Mapping[str, SenseChoice]]


def read_verbs(entries: Mapping[str, Mapping], first_senses: Mapping[str, str]) -> dict[str, PolysemousVerb]:
    """The stored sense lists, or InvalidSenses naming every problem. `first_senses`: verb → its meaning
    (data/meanings.json, English), whose first sense must open the verb's list."""
    verbs = {key: PolysemousVerb(key, tuple(Sense(**sense) for sense in entry.get("senses", ())))
             for key, entry in entries.items()}
    found = [problem for verb in verbs.values() for problem in _verb_problems(verb, first_senses.get(verb.key))]
    if found:
        raise InvalidSenses("; ".join(found))
    return verbs


def read_choices(entries: Mapping[str, Mapping[str, Mapping[str, str]]]) -> dict[str, dict[str, SenseChoice]]:
    """The stored choices, or InvalidSenses naming every malformed one."""
    malformed = [f"{form} {location}: fields {sorted(entry)}, not {sorted(CHOICE_FIELDS)}"
                 for form, by_location in entries.items() for location, entry in by_location.items()
                 if set(entry) != CHOICE_FIELDS or not all(str(value).strip() for value in entry.values())]
    malformed += [f"{form} {location}: not a place in the Quran" for form, by_location in entries.items()
                  for location in by_location if not _LOCATION.match(location)]
    if malformed:
        raise InvalidSenses("; ".join(malformed))
    return {form: {location: SenseChoice(entry["sense"], entry["why"]) for location, entry in by_location.items()}
            for form, by_location in entries.items()}


def stale(choices: Choices, verbs: Mapping[str, PolysemousVerb], places: Mapping[str, Collection[str]]) -> list[str]:
    """Why stored choices no longer fit. `places`: each polysemous form still to compose → where it stands."""
    found = []
    for form, by_location in choices.items():
        verb = verbs.get(verb_of(form))
        if verb is None or form not in places:
            found.append(f"{form}: not a form of a polysemous verb still to compose — drop its choices")
            continue
        found += [f"{form} {location}: the form does not stand there" for location in by_location
                  if location not in places[form]]
        found += [f"{form} {location}: {choice.sense!r} is not a sense of {verb.key}"
                  for location, choice in by_location.items() if not verb.has_sense(choice.sense)]
    return found


def verb_of(form_key: str) -> str:
    """"قضي|1|قَضَىٰ" → "قضي|1"."""
    return "|".join(form_key.split("|")[:2])


def _verb_problems(verb: PolysemousVerb, meaning: str | None) -> list[str]:
    found = []
    if meaning is None:
        found.append(f"{verb.key}: not a studied verb")
    if len(verb.senses) < 2:
        found.append(f"{verb.key}: a polysemous verb needs at least two senses")
        return found
    ids = [sense.id for sense in verb.senses]
    found += [f"{verb.key}: sense id {sense_id!r} repeated" for sense_id in set(ids) if ids.count(sense_id) > 1]
    found += [f"{verb.key}: sense id {sense.id!r} is not a lowercase-hyphenated name"
              for sense in verb.senses if not _SENSE_ID.match(sense.id)]
    found += [problem for sense in verb.senses for problem in _sense_problems(verb.key, sense)]
    if meaning is not None and not found and _sense_of(verb.senses[0].en) != _sense_of(meaning):
        found.append(f"{verb.key}: the first sense must be the verb's own ({meaning!r}), not {verb.senses[0].en!r}")
    return found


def _sense_problems(verb: str, sense: Sense) -> list[str]:
    if not sense.bs.strip():
        return [f"{verb} {sense.id}: no Bosnian"]
    try:
        EnglishVerb.from_meaning(sense.en)
    except CannotCompose:
        return [f"{verb} {sense.id}: {sense.en!r} is not a plain \"to …\" meaning"]
    return []


def _sense_of(meaning: str) -> str | None:
    try:
        return EnglishVerb.from_meaning(meaning).sense
    except CannotCompose:
        return None
