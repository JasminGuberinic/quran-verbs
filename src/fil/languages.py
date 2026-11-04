"""The languages a learner can study Arabic from, and how far each is trusted.

Arabic is learned FROM one of these. They are not equal, and the page must not pretend
they are: English is the language our lexicon checks mechanically, Bosnian is read by a
person, and every other language is a machine translation nobody has reviewed.

Only the ACTIVE languages are offered: the picker, the pages, the sitemap and every card
speak these and no others. The rest are dormant — their translations stay in data/ so a
language comes back by adding its code to ACTIVE, nothing more.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypeVar

LEXICON_CHECKED = "lexicon-checked"   # agreed with the CAMeL lexicon's English glosses
PERSON_READ = "person-read"           # a person reads it (no scholar yet)
MACHINE = "machine"                   # AI translation, unreviewed


@dataclass(frozen=True)
class Language:
    code: str
    name: str            # in the language itself, as its speakers would pick it
    is_rtl: bool
    trust: str


# Every language we have ever translated into, active or dormant.
KNOWN: tuple[Language, ...] = (
    Language("bs", "Bosanski", False, PERSON_READ),
    Language("en", "English", False, LEXICON_CHECKED),
    Language("tr", "Türkçe", False, MACHINE),
    Language("de", "Deutsch", False, MACHINE),
    Language("sq", "Shqip", False, MACHINE),
    Language("fr", "Français", False, MACHINE),
    Language("id", "Bahasa Indonesia", False, MACHINE),
    Language("ur", "اردو", True, MACHINE),
    Language("bn", "বাংলা", False, MACHINE),
    Language("fa", "فارسی", True, MACHINE),
    Language("ru", "Русский", False, MACHINE),
    Language("ms", "Bahasa Melayu", False, MACHINE),
    Language("es", "Español", False, MACHINE),
    Language("sw", "Kiswahili", False, MACHINE),
    Language("so", "Soomaali", False, MACHINE),
    Language("hi", "हिन्दी", False, MACHINE),
)

# The languages the site offers, in the order the picker lists them.
ACTIVE: tuple[str, ...] = ("bs", "en", "tr", "fr", "id", "ur", "bn", "fa")


def _active_languages() -> tuple[Language, ...]:
    """ACTIVE, resolved and checked once at import: a typo fails fast, never a missing page."""
    known = {language.code: language for language in KNOWN}
    unknown = [code for code in ACTIVE if code not in known]
    if unknown:
        raise ValueError(f"ACTIVE names languages that are not KNOWN: {', '.join(unknown)}")
    return tuple(known[code] for code in ACTIVE)


LANGUAGES: tuple[Language, ...] = _active_languages()
CODES: tuple[str, ...] = tuple(language.code for language in LANGUAGES)

# Every verb must be complete in these before it ships; the rest are translated later, in
# bulk, and fall back to English on the page until then (labelled as such).
REQUIRED: tuple[str, ...] = ("bs", "en")


Value = TypeVar("Value")


def only_active(by_language: Mapping[str, Value]) -> dict[str, Value]:
    """The entries of a {language: ...} map that a learner can be shown; dormant ones stay in data/."""
    return {code: value for code, value in by_language.items() if code in CODES}

