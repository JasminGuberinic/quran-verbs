"""The root pages, built from the catalogues, our pages and our meanings — pure.

A root gets a page when at least one of its words is studied (it has a card, or a particle page).
Every catalogued word of the root is listed, studied or not: verbs by form, then nouns, adjectives
and participles, most frequent first. A word's meaning is its card's; an unstudied word shows one
only where our data holds a vetted meaning for it (fil.stages.roots gathers them), never a guess.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from fil.nuances.model import Text
from fil.roots.model import SECTIONS, CoreIdea, ListedWord, RootPage, RootWord, StudiedPage

# The Arabic alphabet, in its order: the list of roots is alphabetical, as a dictionary of roots is.
ALPHABET = "ابتثجحخدذرزسشصضطظعغفقكلمنهوي"
_SAME_LETTER = {"ء": "ا", "أ": "ا", "إ": "ا", "آ": "ا", "ؤ": "ا", "ئ": "ا"}   # every hamza files under alif


@dataclass(frozen=True)
class RootSources:
    """Everything a root page is made from, by word key ("قول_1", "قَوْل|قول") or by root."""

    words: Sequence[RootWord]
    corpus_counts: Mapping[str, int]                      # root → the corpus's words of that root
    corrected_counts: Mapping[str, int] = field(default_factory=dict)   # root → words corrected away
    pages: Mapping[str, tuple[StudiedPage, ...]] = field(default_factory=dict)
    meanings: Mapping[str, Text] = field(default_factory=dict)         # vetted meanings of words
    nuance_groups: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    core_ideas: Mapping[str, CoreIdea] = field(default_factory=dict)
    slugs: Mapping[str, str] = field(default_factory=dict)


def root_pages(sources: RootSources) -> tuple[RootPage, ...]:
    """A page per root with a studied word, in alphabetical order."""
    by_root: dict[str, list[RootWord]] = defaultdict(list)
    for word in sources.words:
        by_root[word.root].append(word)
    studied_roots = [root for root, words in by_root.items() if any(word.key in sources.pages for word in words)]
    return tuple(_page(root, by_root[root], sources) for root in sorted(studied_roots, key=alphabetical_key))


def alphabetical_key(root: str) -> tuple[int, ...]:
    return tuple(ALPHABET.index(first_letter(letter)) for letter in root)


def first_letter(letter: str) -> str:
    """The letter a root is filed under in the alphabetical index (every hamza under alif)."""
    return _SAME_LETTER.get(letter, letter)


def _page(root: str, words: Sequence[RootWord], sources: RootSources) -> RootPage:
    listed = [_listed(word, sources) for word in words]
    sections = tuple((section, tuple(sorted((word for word in listed if word.word.section == section), key=_reading_order)))
                     for section in SECTIONS)
    groups = tuple(dict.fromkeys(slug for word in words for slug in sources.nuance_groups.get(word.key, ())))
    return RootPage(root=root, slug=sources.slugs[root], corpus_count=sources.corpus_counts.get(root, 0),
                    corrected_count=sources.corrected_counts.get(root, 0),
                    sections=tuple((section, found) for section, found in sections if found),
                    nuance_groups=groups, core=sources.core_ideas.get(root))


def _listed(word: RootWord, sources: RootSources) -> ListedWord:
    pages = sources.pages.get(word.key, ())
    meaning = pages[0].meaning if pages else sources.meanings.get(word.key)
    return ListedWord(word=word, meaning=meaning, pages=pages)


def _reading_order(listed: ListedWord) -> tuple:
    """Verbs by form (I before II…); every other word most frequent first."""
    word = listed.word
    return (word.form or 0, -word.count, word.arabic) if word.is_verb else (-word.count, word.arabic)


def pages_by_word(pages: Iterable[tuple[str, StudiedPage]]) -> dict[str, tuple[StudiedPage, ...]]:
    """(word key, page) pairs gathered per word, in the order given (a card before a particle page)."""
    gathered: dict[str, list[StudiedPage]] = defaultdict(list)
    for key, page in pages:
        if page not in gathered[key]:
            gathered[key].append(page)
    return {key: tuple(found) for key, found in gathered.items()}
