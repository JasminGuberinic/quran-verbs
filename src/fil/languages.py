"""The languages a learner can study Arabic from, and how far each is trusted.

Arabic is learned FROM one of these. They are not equal, and the page must not pretend
they are: English is the language our lexicon checks mechanically, Bosnian is read by a
person, and every other language is a machine translation nobody has reviewed.
"""

from __future__ import annotations

from dataclasses import dataclass

LEXICON_CHECKED = "lexicon-checked"   # agreed with the CAMeL lexicon's English glosses
PERSON_READ = "person-read"           # a person reads it (no scholar yet)
MACHINE = "machine"                   # AI translation, unreviewed


@dataclass(frozen=True)
class Language:
    code: str
    name: str            # in the language itself, as its speakers would pick it
    is_rtl: bool
    trust: str


LANGUAGES: tuple[Language, ...] = (
    Language("bs", "Bosanski", False, PERSON_READ),
    Language("en", "English", False, LEXICON_CHECKED),
    Language("tr", "Türkçe", False, MACHINE),
    Language("de", "Deutsch", False, MACHINE),
    Language("sq", "Shqip", False, MACHINE),
    Language("fr", "Français", False, MACHINE),
    Language("id", "Bahasa Indonesia", False, MACHINE),
    Language("ur", "اردو", True, MACHINE),
)

CODES: tuple[str, ...] = tuple(language.code for language in LANGUAGES)
