"""What a surah page is made of. Pure data, validated where it is built.

A *token* is one whole word of the Quran as the corpus numbers it (surah:ayah:word) — the unit a
reader sees between two spaces, and the unit coverage is counted in. Each token is headed by one
*headword* (fil.surahs.headword): the word a learner would look up. A headword the site teaches
is `Taught`: it has a card, and a vetted meaning on it.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from fil.quran_numbering import SURAH_AYAH_COUNTS

# What heads a token, as the corpus lets us tell it.
VERB, NOUN, PARTICLE, PRONOUN, OTHER = "verb", "noun", "particle", "pronoun", "other"
HEADWORD_KINDS = (VERB, NOUN, PARTICLE, PRONOUN, OTHER)
# The site's word families a taught headword's card belongs to.
FAMILIES = ("verb", "noun", "adjective", "particle", "pronoun")
MECCAN, MEDINAN = "meccan", "medinan"
Location = tuple[int, int, int]           # (surah, ayah, word)

_LONG_VOWELS = (("aa", "a"), ("ii", "i"), ("uu", "u"), ("oo", "u"), ("ee", "i"))


class InvalidSurahData(ValueError):
    """Surah metadata that does not describe the Quran the corpus holds."""


@dataclass(frozen=True)
class Surah:
    """One surah as Tanzil's metadata names it."""

    number: int
    arabic: str                  # its name, as Tanzil writes it: البقرة
    transliteration: str         # Al-Baqara
    english: str                 # The Cow
    revelation: str              # MECCAN or MEDINAN
    ayah_count: int

    def __post_init__(self) -> None:
        if not 1 <= self.number <= len(SURAH_AYAH_COUNTS):
            raise InvalidSurahData(f"surah {self.number}: there are {len(SURAH_AYAH_COUNTS)} surahs")
        if self.ayah_count != SURAH_AYAH_COUNTS[self.number - 1]:
            raise InvalidSurahData(f"surah {self.number}: {self.ayah_count} ayat, the numbering says "
                                   f"{SURAH_AYAH_COUNTS[self.number - 1]}")
        if self.revelation not in (MECCAN, MEDINAN):
            raise InvalidSurahData(f"surah {self.number}: revelation {self.revelation!r} is neither {MECCAN} nor {MEDINAN}")
        if not self.arabic or not self.transliteration:
            raise InvalidSurahData(f"surah {self.number}: a surah needs its Arabic name and a transliteration")

    @property
    def slug(self) -> str:
        """"2-al-baqara": its number first, so it never changes and never collides; then a readable name."""
        return f"{self.number}-{name_slug(self.transliteration)}"


def name_slug(transliteration: str) -> str:
    """Tanzil's "Aal-i-Imraan" → "al-i-imran": lowercase ASCII, long vowels written once."""
    reading = transliteration.lower().replace("'", "")
    for long, short in _LONG_VOWELS:
        reading = reading.replace(long, short)
    return re.sub(r"[^a-z0-9]+", "-", reading).strip("-")


@dataclass(frozen=True)
class Headword:
    """The word a token is looked up under. `key` names it within its kind (how the site's cards are
    keyed: a verb "root_form", a noun "lemma|root", a particle "lemma|TAG", a pronoun "name|TAG");
    `arabic` is how a list shows it."""

    kind: str
    key: str
    arabic: str

    def __post_init__(self) -> None:
        if self.kind not in HEADWORD_KINDS:
            raise ValueError(f"headword kind {self.kind!r} is not one of {HEADWORD_KINDS}")

    @property
    def group(self) -> str:
        """What an entry gathers when nothing we teach does: a particle by its lemma, whatever its use
        (the corpus's tags tell the uses apart; a list of words does not), anything else by its key."""
        if self.kind == PARTICLE:
            return f"{PARTICLE}:{self.key.split('|', 1)[0]}"
        return f"{self.kind}:{self.key}"


@dataclass(frozen=True)
class Token:
    surah: int
    ayah: int
    word: int
    text: str                    # the whole word as the Quran writes it, clitics and all
    headword: Headword

    @property
    def location(self) -> Location:
        return (self.surah, self.ayah, self.word)


@dataclass(frozen=True)
class Taught:
    """A headword with a card on the site: its family's page, how the card writes it, what it means."""

    family: str
    slug: str
    arabic: str
    meaning: Mapping[str, str]   # vetted, from the card: {"bs": …, "en": …}
    root: str | None = None      # the root's letters, for a verb, noun or adjective

    def __post_init__(self) -> None:
        if self.family not in FAMILIES:
            raise ValueError(f"family {self.family!r} is not one of {FAMILIES}")

    @property
    def group(self) -> str:
        return f"{self.family}:{self.slug}"
