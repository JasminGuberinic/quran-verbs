"""What a root page is made of: the words of a root, the cards they link to, the page itself.

Pure data and pure rules. A word is one entry of our catalogues — a verb by root and form
(قول_1), a noun, adjective or participle by lemma and root (قَوْل|قول) — so a root page counts
exactly what the verb, noun and adjective cards count.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from fil.nuances.model import Text

# The sections of a root page, in reading order.
VERBS, NOUNS, ADJECTIVES, PARTICIPLES = "verbs", "nouns", "adjectives", "participles"
SECTIONS = (VERBS, NOUNS, ADJECTIVES, PARTICIPLES)

# The kinds of word the catalogues know (fil.corpus.catalog for verbs, fil.nouns.catalogue for the rest).
VERB = "verb"
NOUN, VERBAL_NOUN, ADVERB, PROPER_NOUN, ADJECTIVE = "noun", "verbal_noun", "adverb", "proper_noun", "adjective"
ACTIVE_PARTICIPLE, PASSIVE_PARTICIPLE = "active_participle", "passive_participle"
_SECTION_OF_KIND = {VERB: VERBS, NOUN: NOUNS, VERBAL_NOUN: NOUNS, ADVERB: NOUNS, PROPER_NOUN: NOUNS, ADJECTIVE: ADJECTIVES,
                    ACTIVE_PARTICIPLE: PARTICIPLES, PASSIVE_PARTICIPLE: PARTICIPLES}

# The pages a word may link to.
VERB_PAGE, NOUN_PAGE, ADJECTIVE_PAGE, PARTICLE_PAGE = "verb", "noun", "adjective", "particle"
PAGE_KINDS = (VERB_PAGE, NOUN_PAGE, ADJECTIVE_PAGE, PARTICLE_PAGE)

# The pattern of each verb form, on the model root ف ع ل (a four-letter root: ف ع ل ل).
_TRILITERAL_PATTERNS = {1: "فَعَلَ", 2: "فَعَّلَ", 3: "فَاعَلَ", 4: "أَفْعَلَ", 5: "تَفَعَّلَ", 6: "تَفَاعَلَ",
                        7: "اِنْفَعَلَ", 8: "اِفْتَعَلَ", 9: "اِفْعَلَّ", 10: "اِسْتَفْعَلَ"}
_QUADRILITERAL_PATTERNS = {1: "فَعْلَلَ", 2: "تَفَعْلَلَ", 4: "اِفْعَلَلَّ"}
FORM_NAMES = ("", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X")

MUFRADAT = "0502RaghibIsbahani.Mufradat.JK001150-ara1"   # the OpenITI version a core idea is checked against
_MAXIMUM_CORE_LENGTH = 200
_DOUBLE_QUOTES = re.compile(r"[\"“”„«»]")   # a core idea quotes no ayah: double marks would claim one


class InvalidRootData(ValueError):
    """A stored core idea that may not reach a page."""


class UnknownVerbForm(ValueError):
    """A verb form the patterns do not know."""


@dataclass(frozen=True)
class RootWord:
    """One word of the catalogues under its root."""

    key: str            # a verb "قول_1"; any other word "قَوْل|قول"
    root: str
    arabic: str
    kind: str           # VERB, NOUN, VERBAL_NOUN, ADVERB, PROPER_NOUN, ADJECTIVE, ACTIVE_PARTICIPLE, PASSIVE_PARTICIPLE
    count: int
    form: int | None = None   # a verb's form; the form a participle or verbal noun derives from, where known

    def __post_init__(self) -> None:
        if self.kind not in _SECTION_OF_KIND:
            raise ValueError(f"{self.key}: unknown kind of word {self.kind!r}")
        if self.kind == VERB and self.form is None:
            raise ValueError(f"{self.key}: a verb needs its form")

    @property
    def section(self) -> str:
        return _SECTION_OF_KIND[self.kind]

    @property
    def is_verb(self) -> bool:
        return self.kind == VERB


@dataclass(frozen=True)
class StudiedPage:
    """One of our pages a word links to: its card (verb, noun, adjective) or its particle page."""

    kind: str           # one of PAGE_KINDS
    slug: str
    meaning: Text
    audio: str | None   # the word said, as its card says it (a published clip), or None

    def __post_init__(self) -> None:
        if self.kind not in PAGE_KINDS:
            raise ValueError(f"{self.slug}: unknown kind of page {self.kind!r}")


@dataclass(frozen=True)
class ListedWord:
    """A word as its root page lists it: its meaning only where our data vets one, its pages if studied."""

    word: RootWord
    meaning: Text | None
    pages: tuple[StudiedPage, ...] = ()

    @property
    def is_studied(self) -> bool:
        return bool(self.pages)

    @property
    def audio(self) -> str | None:
        return next((page.audio for page in self.pages if page.audio), None)


@dataclass(frozen=True)
class CoreIdea:
    """The idea a root's words share, in our own words, checked against ar-Rāġib's Mufradāt entry."""

    root: str
    text: Text
    entries: tuple[str, ...]   # the Mufradāt headwords read, as the book spells them
    notes: str


@dataclass(frozen=True)
class RootPage:
    """One root: its letters, its page name, how often the corpus has it, and its words by section."""

    root: str
    slug: str
    corpus_count: int           # the corpus's words of this root
    corrected_count: int        # of them, words our documented corrections read as another word
    sections: tuple[tuple[str, tuple[ListedWord, ...]], ...]
    nuance_groups: tuple[str, ...] = ()   # the slugs of the near-synonym groups holding one of its words
    core: CoreIdea | None = None

    @property
    def letters(self) -> str:
        """ق و ل — the root as it is read aloud, letter by letter."""
        return " ".join(self.root)

    @property
    def words(self) -> tuple[ListedWord, ...]:
        return tuple(word for _, words in self.sections for word in words)

    @property
    def studied(self) -> tuple[ListedWord, ...]:
        """The words we teach, most frequent first."""
        return tuple(sorted((word for word in self.words if word.is_studied), key=lambda word: -word.word.count))

    @property
    def listed_count(self) -> int:
        return sum(word.word.count for word in self.words)


def verb_pattern(root: str, form: int) -> str:
    """The form's pattern on the model root: فَعَّلَ for Form II, فَعْلَلَ for a four-letter root's Form I."""
    patterns = _QUADRILITERAL_PATTERNS if len(root) == 4 else _TRILITERAL_PATTERNS
    if form not in patterns:
        raise UnknownVerbForm(f"{root}: no pattern for Form {form}")
    return patterns[form]


# ---------------------------------------------------------------- page names

# A root's page name reads its letters: ق و ل → q-w-l. ʿayn is spelled out; every hamza is "a".
_LETTERS = {
    "ب": "b", "ت": "t", "ث": "th", "ج": "j", "ح": "h", "خ": "kh", "د": "d", "ذ": "dh",
    "ر": "r", "ز": "z", "س": "s", "ش": "sh", "ص": "s", "ض": "d", "ط": "t", "ظ": "z",
    "ع": "ayn", "غ": "gh", "ف": "f", "ق": "q", "ك": "k", "ل": "l", "م": "m", "ن": "n",
    "ه": "h", "و": "w", "ي": "y", "ء": "a", "أ": "a", "إ": "a", "ؤ": "a", "ئ": "a", "ا": "a",
}


def slug_of(root: str) -> str:
    try:
        return "-".join(_LETTERS[letter] for letter in root)
    except KeyError as missing:
        raise ValueError(f"{root}: no ASCII reading for the letter {missing}") from None


def assign_slugs(roots_by_frequency: Iterable[str]) -> dict[str, str]:
    """One page name per root, decided over every root of the corpus, most frequent first: ح and ه,
    ص and س read alike, so the more frequent root keeps the plain name and the next takes -2. The
    corpus is fixed, so a published name never changes when another root gets a page."""
    taken: set[str] = set()
    slugs: dict[str, str] = {}
    for root in roots_by_frequency:
        slug = _free_variant(slug_of(root), taken)
        taken.add(slug)
        slugs[root] = slug
    return slugs


def _free_variant(base: str, taken: set[str]) -> str:
    suffix = 1
    candidate = base
    while candidate in taken:
        suffix += 1
        candidate = f"{base}-{suffix}"
    return candidate


# ---------------------------------------------------------------- core ideas

def parse_core_ideas(entries: Mapping[str, Mapping]) -> tuple[CoreIdea, ...]:
    """`{"<root>": {"core": {"bs", "en"}, "verified": [{"source", "entries"}], "notes"}}` → core ideas.

    Fails fast on a missing language, a text too long to be one line, double quotation marks (a
    core idea quotes no ayah), or a missing record of what was read in the Mufradāt."""
    return tuple(_core_idea(root, entry) for root, entry in entries.items())


def _core_idea(root: str, entry: Mapping) -> CoreIdea:
    core = entry.get("core") or {}
    text = Text(bs=_line(root, core, "bs"), en=_line(root, core, "en"))
    return CoreIdea(root=root, text=text, entries=_verified_entries(root, entry), notes=_notes(root, entry))


def _line(root: str, core: Mapping, language: str) -> str:
    line = (core.get(language) or "").strip()
    if not line:
        raise InvalidRootData(f"{root}: the core idea has no {language} text")
    if len(line) > _MAXIMUM_CORE_LENGTH:
        raise InvalidRootData(f"{root}: the {language} core idea is longer than one line ({len(line)} characters)")
    if _DOUBLE_QUOTES.search(line):
        raise InvalidRootData(f"{root}: the {language} core idea has double quotation marks, which quote an ayah")
    return line


def _verified_entries(root: str, entry: Mapping) -> tuple[str, ...]:
    records = entry.get("verified") or []
    entries = tuple(headword for record in records if record.get("source") == MUFRADAT
                    for headword in record.get("entries") or ())
    if not entries:
        raise InvalidRootData(f"{root}: a core idea must record the Mufradāt entries it was verified against ({MUFRADAT})")
    return entries


def _notes(root: str, entry: Mapping) -> str:
    notes = (entry.get("notes") or "").strip()
    if not notes:
        raise InvalidRootData(f"{root}: a core idea must say in its notes what was confirmed in the Mufradāt")
    return notes
