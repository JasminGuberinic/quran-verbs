"""A surah's vocabulary: its tokens grouped under the words a learner looks up, and how many we teach.

Every token of the surah lands in exactly one entry: under the card that teaches its headword
(every use of وَ the particle page explains goes to that one page), or — when no card does —
under its headword as the corpus names it. Coverage is the share of the surah's tokens whose
headword has a card: "of every 100 words you read in this surah, the site teaches N".

The gate (`problems`) holds the account to the surah itself: every ayah from 1 to its last, every
word of each from 1 on, each counted once — so a page never claims a coverage of words it lost.

Pure: tokens and a teaching lookup in, a SurahVocabulary out.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from itertools import groupby

from fil.surahs.model import Headword, Location, Surah, Taught, Token

# Which card, if any, teaches a headword.
Teaching = Callable[[Headword], Taught | None]


class SurahNotAccountedFor(ValueError):
    """A surah's tokens, or its entries, do not add up to the surah."""


@dataclass(frozen=True)
class Entry:
    """One word of the surah's vocabulary and every token it stands for, in reading order."""

    headword: Headword            # the headword of its first token
    taught: Taught | None
    tokens: tuple[Token, ...]

    @property
    def key(self) -> str:
        return self.taught.group if self.taught else self.headword.group

    @property
    def count(self) -> int:
        return len(self.tokens)

    @property
    def first(self) -> Token:
        return self.tokens[0]

    @property
    def forms(self) -> tuple[tuple[str, int], ...]:
        """Each way the surah writes it (the whole word, clitics and all) and how often, first seen first."""
        return tuple(Counter(token.text for token in self.tokens).items())

    @property
    def is_taught(self) -> bool:
        return self.taught is not None


@dataclass(frozen=True)
class SurahVocabulary:
    surah: Surah
    tokens: tuple[Token, ...]
    entries: tuple[Entry, ...]    # in order of first appearance

    @property
    def covered(self) -> int:
        """How many of the surah's tokens are headed by a word we teach."""
        return sum(entry.count for entry in self.entries if entry.is_taught)

    @property
    def coverage(self) -> float:
        return self.covered / len(self.tokens)

    @property
    def coverage_percent(self) -> int:
        """Coverage as a whole percentage, rounded down: a page never claims more than it teaches."""
        return self.covered * 100 // len(self.tokens)

    @property
    def taught(self) -> tuple[Entry, ...]:
        return tuple(entry for entry in self.entries if entry.is_taught)

    @property
    def untaught(self) -> tuple[Entry, ...]:
        return tuple(entry for entry in self.entries if not entry.is_taught)


def vocabulary_of(surah: Surah, tokens: Sequence[Token], teaching: Teaching) -> SurahVocabulary:
    """The surah's entries, in order of first appearance; refused when the tokens are not the whole surah."""
    tokens = tuple(tokens)
    vocabulary = SurahVocabulary(surah, tokens, tuple(_entries(tokens, teaching)))
    found = problems(vocabulary)
    if found:
        raise SurahNotAccountedFor(f"surah {surah.number}: {len(found)} problems, e.g. {found[:3]}")
    return vocabulary


def by_frequency(entries: Iterable[Entry]) -> list[Entry]:
    """The most frequent in the surah first; equals in the order the surah first uses them."""
    ranked = sorted(enumerate(entries), key=lambda numbered: (-numbered[1].count, numbered[0]))
    return [entry for _position, entry in ranked]


def _entries(tokens: Sequence[Token], teaching: Teaching) -> list[Entry]:
    grouped: dict[str, list[Token]] = {}
    taught_by: dict[str, Taught | None] = {}
    for token in tokens:
        taught = teaching(token.headword)
        key = taught.group if taught else token.headword.group
        grouped.setdefault(key, []).append(token)
        taught_by.setdefault(key, taught)
    return [Entry(found[0].headword, taught_by[key], tuple(found)) for key, found in grouped.items()]


# ---------------------------------------------------------------- the gate

def problems(vocabulary: SurahVocabulary) -> list[str]:
    """Every way the vocabulary fails to account for its surah; none when each token is in exactly one entry."""
    return [*_token_problems(vocabulary.surah, vocabulary.tokens), *_entry_problems(vocabulary)]


def _token_problems(surah: Surah, tokens: Sequence[Token]) -> list[str]:
    if not tokens:
        return [f"surah {surah.number} has no tokens"]
    found = [f"{token.surah}:{token.ayah}:{token.word} is not in surah {surah.number}"
             for token in tokens if token.surah != surah.number]
    ayat = [ayah for ayah, _words in groupby(tokens, key=lambda token: token.ayah)]
    if ayat != list(range(1, surah.ayah_count + 1)):
        found.append(f"surah {surah.number}: ayat {_span(ayat)} in reading order, not 1–{surah.ayah_count}")
    for ayah, words in groupby(tokens, key=lambda token: token.ayah):
        numbers = [token.word for token in words]
        if numbers != list(range(1, len(numbers) + 1)):
            found.append(f"{surah.number}:{ayah}: words {_span(numbers)}, not 1–{len(numbers)} in order")
    return found


def _entry_problems(vocabulary: SurahVocabulary) -> list[str]:
    placed = Counter(token.location for entry in vocabulary.entries for token in entry.tokens)
    surah: set[Location] = {token.location for token in vocabulary.tokens}
    found = [f"{_where(location)} is in {count} entries" for location, count in placed.items() if count > 1]
    found += [f"{_where(location)} is in no entry" for location in sorted(surah - set(placed))]
    found += [f"{_where(location)} is in an entry but not in the surah" for location in sorted(set(placed) - surah)]
    keys = Counter(entry.key for entry in vocabulary.entries)
    found += [f"entry {key} is listed {count} times" for key, count in keys.items() if count > 1]
    if sum(entry.count for entry in vocabulary.entries) != len(vocabulary.tokens):
        found.append(f"the entries count {sum(entry.count for entry in vocabulary.entries)} tokens, "
                     f"the surah has {len(vocabulary.tokens)}")
    return found


def _where(location: Location) -> str:
    return ":".join(map(str, location))


def _span(numbers: Sequence[int]) -> str:
    return f"{numbers[0]}…{numbers[-1]} ({len(numbers)})" if numbers else "none"
