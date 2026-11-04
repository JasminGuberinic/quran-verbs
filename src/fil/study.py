"""What a learner studies for one verb, chosen from the Quran itself.

Pure decisions over the corpus — no downloads, no files — so every choice is testable
on a handful of synthetic segments:

  - which ayat show the verb: up to six, each a different form of it (past "he said",
    past "they said", present, command …), the forms it is used in most, each in an ayah
    as short as the Quran allows;
  - where a conjugated form stands on its own as a whole word, so it can be heard
    exactly as it is recited;
  - the verb's active participle and verbal noun, taken from the corpus tags rather than
    derived by rule, so a learner meets the nouns the Quran actually uses.

Only active-voice occurrences count: a passive form looks like the verb but means the
opposite direction, and would teach the wrong thing.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import groupby
from typing import Iterable, Sequence

from fil.attested_forms import FormOccurrence
from fil.corpus.corrections import CorpusCorrections, apply_corrections
from fil.corpus.parse import Segment, iter_verb_occurrences

VerbKey = tuple[str, int]                 # (root, form)
Location = tuple[int, int, int]           # (surah, ayah, word)

# The tenses an ayah can illustrate, in teaching order.
TENSES = ("past", "present", "imperative")

# An ayah longer than this is hard to take in while learning a single word.
MAX_AYAH_WORDS = 12
MIN_AYAH_WORDS = 3

# How many example ayat a verb shows at most: one per form, so they never repeat one.
MAX_EXAMPLES = 6

# A form an example ayah stands for: who does it, and when — "past · they (m.)".
Category = tuple[str, str]               # (tense, pronoun key)


@dataclass(frozen=True)
class QuranWord:
    """One whole word of the Quran: its text and the active verbs it carries."""

    surah: int
    ayah: int
    number: int
    text: str
    verbs: frozenset[tuple[str, int, str]] = frozenset()   # (root, form, tense)

    @property
    def location(self) -> Location:
        return (self.surah, self.ayah, self.number)

    def carries(self, verb: VerbKey, tense: str | None = None) -> bool:
        """Whether this word holds the verb (optionally in one tense)."""
        return any(
            (root, form) == verb and (tense is None or used_tense == tense)
            for root, form, used_tense in self.verbs
        )


@dataclass(frozen=True)
class AyahExample:
    """An ayah that shows a verb, and which of its words is the verb."""

    surah: int
    ayah: int
    tense: str
    words: tuple[QuranWord, ...]
    pronoun: str = ""            # with `tense`, the form this ayah stands for

    @property
    def ref(self) -> str:
        return f"{self.surah}:{self.ayah}"

    @property
    def category(self) -> Category:
        return (self.tense, self.pronoun)


@dataclass(frozen=True)
class DerivedNoun:
    """A noun built on the verb (participle or verbal noun), as the Quran uses it."""

    lemma: str
    count: int


def words_of(segments: Iterable[Segment], corrections: CorpusCorrections) -> tuple[QuranWord, ...]:
    """Join segments into whole words, tagging each with the active verbs inside it.

    A word the corrections say the corpus misfiled is not tagged with that verb, so it
    never becomes one of its example ayat; a mis-tensed one is tagged with its true tense.
    """
    segments = list(segments)
    active_verbs = defaultdict(set)
    occurrences = apply_corrections(iter_verb_occurrences(iter(segments)), corrections)
    for occurrence in occurrences:
        if not occurrence.passive:
            active_verbs[(occurrence.surah, occurrence.ayah, occurrence.word)].add(
                (occurrence.root, occurrence.form, occurrence.tense)
            )
    return tuple(
        QuranWord(surah, ayah, number, "".join(part.surface for part in parts),
                  frozenset(active_verbs[(surah, ayah, number)]))
        for (surah, ayah, number), parts in groupby(
            segments, key=lambda segment: (segment.surah, segment.ayah, segment.word)
        )
    )


def ayat_of(words: Iterable[QuranWord]) -> dict[tuple[int, int], tuple[QuranWord, ...]]:
    """Every ayah as its words, in order."""
    return {
        key: tuple(group)
        for key, group in groupby(words, key=lambda word: (word.surah, word.ayah))
    }


def example_ayat(ayat: dict[tuple[int, int], tuple[QuranWord, ...]], verb: VerbKey,
                 uses: Sequence[FormOccurrence]) -> list[AyahExample]:
    """Up to MAX_EXAMPLES short ayat, each showing the verb in a different form, the commonest first.

    The ayat chosen one per tense (`_one_per_tense`) always stay: their verbs are already
    glossed and translated. The other places go to the forms the verb is used in most that
    those do not show yet, each in its shortest ayah. Only active uses count, and only ayat
    of MIN_AYAH_WORDS..MAX_AYAH_WORDS words; ties go to the earlier ayah, so the choice is
    stable from one build to the next.
    """
    categories = active_categories(uses)
    ranked = ranked_categories(categories)
    chosen = [_categorized(example, verb, categories, ranked) for example in _one_per_tense(ayat, verb)]
    for category in ranked:
        if len(chosen) >= MAX_EXAMPLES:
            break
        if category in {example.category for example in chosen}:
            continue
        found = _shortest_ayah_showing(ayat, categories, category, {(e.surah, e.ayah) for e in chosen})
        if found:
            chosen.append(found)
    return sorted(chosen, key=lambda example: ranked.index(example.category))


def active_categories(uses: Iterable[FormOccurrence]) -> dict[Location, Category]:
    """The form (tense, pronoun) of each active use of a verb, by where it stands."""
    return {use.location: (use.grammar.tense, use.grammar.pronoun) for use in uses if not use.grammar.is_passive}


def ranked_categories(categories: dict[Location, Category]) -> list[Category]:
    """The verb's forms, the most used first; ties go to the form the Quran uses first."""
    counts = Counter(categories.values())
    first_seen = {category: location for location, category in sorted(categories.items(), reverse=True)}
    return sorted(counts, key=lambda category: (-counts[category], first_seen[category]))


def _one_per_tense(ayat: dict[tuple[int, int], tuple[QuranWord, ...]], verb: VerbKey) -> list[AyahExample]:
    """One short ayah per tense the verb is used in, never the same ayah twice — shortest first."""
    chosen: list[AyahExample] = []
    used: set[tuple[int, int]] = set()
    for tense in TENSES:
        candidates = [
            (key, words) for key, words in ayat.items()
            if key not in used and _is_short(words) and any(word.carries(verb, tense) for word in words)
        ]
        if not candidates:
            continue
        key, words = min(candidates, key=lambda item: (len(item[1]), item[0]))
        used.add(key)
        chosen.append(AyahExample(key[0], key[1], tense, words))
    return chosen


def _categorized(example: AyahExample, verb: VerbKey, categories: dict[Location, Category],
                 ranked: list[Category]) -> AyahExample:
    """A tense's ayah named by the commonest form of that tense its verb takes there."""
    shown = [categories[word.location] for word in example.words
             if word.carries(verb, example.tense) and word.location in categories]
    if not shown:
        raise ValueError(f"{example.ref}: the corpus gives no form for {verb} in the {example.tense}")
    tense, pronoun = min(shown, key=ranked.index)
    return AyahExample(example.surah, example.ayah, tense, example.words, pronoun)


def _shortest_ayah_showing(ayat: dict[tuple[int, int], tuple[QuranWord, ...]], categories: dict[Location, Category],
                           category: Category, used: set[tuple[int, int]]) -> AyahExample | None:
    keys = {location[:2] for location, shown in categories.items() if shown == category}
    candidates = [(key, ayat[key]) for key in keys if key not in used and key in ayat and _is_short(ayat[key])]
    if not candidates:
        return None
    key, words = min(candidates, key=lambda item: (len(item[1]), item[0]))
    return AyahExample(key[0], key[1], category[0], words, category[1])


def _is_short(words: tuple[QuranWord, ...]) -> bool:
    return MIN_AYAH_WORDS <= len(words) <= MAX_AYAH_WORDS


def standalone_locations(words: Iterable[QuranWord]) -> dict[str, Location]:
    """Where each exact word first stands alone — the place to hear it recited as written.

    A form glued to a prefix (فَٱعْلَمْ) is not the form on its own, so only an exact match
    of the whole word counts.
    """
    located: dict[str, Location] = {}
    for word in words:
        located.setdefault(word.text, word.location)
    return located


# Clitics that can sit in front of a verb without changing how the verb itself is said:
# "and", "so", the oath/emphasis lām, the question hamza, the future sīn.
_PROCLITICS = ("وَ", "فَ", "لَ", "وَلَ", "فَلَ", "أَ", "أَفَ", "أَوَ", "سَ")


@dataclass(frozen=True)
class Recitation:
    """Where a form can be heard recited, and the exact word the reciter says there."""

    location: Location
    text: str


def recitation_index(words: Iterable[QuranWord]) -> dict[str, Recitation]:
    """For each form, the first place it is recited — alone if possible, else behind a clitic.

    A form standing alone is heard exactly as written. When the Quran only has it behind
    "and"/"so" (فَٱعْلَمْ), that whole word is offered instead and shown as such, so the
    learner always sees what they hear. A form never recited gets no entry: no sound is
    better than a machine guessing at the vowels.
    """
    words = list(words)
    index: dict[str, Recitation] = {}
    for word in words:
        index.setdefault(word.text, Recitation(word.location, word.text))
    for word in words:
        for clitic in _PROCLITICS:
            if word.text.startswith(clitic) and len(word.text) > len(clitic):
                index.setdefault(word.text[len(clitic):], Recitation(word.location, word.text))
    return index


def derived_nouns(segments: Iterable[Segment]) -> dict[VerbKey, dict[str, DerivedNoun]]:
    """The commonest active participle and verbal noun of each verb, by corpus tag."""
    counts: dict[tuple[VerbKey, str], Counter] = defaultdict(Counter)
    for segment in segments:
        kind = _noun_kind(segment)
        root, form, lemma = _tag(segment, "ROOT"), _tag(segment, "VF"), _tag(segment, "LEM")
        if kind and root and lemma:
            counts[((root, int(form or 1)), kind)][lemma] += 1

    nouns: dict[VerbKey, dict[str, DerivedNoun]] = defaultdict(dict)
    for (verb, kind), lemmas in counts.items():
        lemma, count = lemmas.most_common(1)[0]
        nouns[verb][kind] = DerivedNoun(lemma, count)
    return dict(nouns)


_NOUN_KINDS = {"ACT_PCPL": "participle", "VN": "verbal_noun"}


def _noun_kind(segment: Segment) -> str | None:
    if segment.pos != "N":
        return None
    return next((_NOUN_KINDS[tag] for tag in segment.features if tag in _NOUN_KINDS), None)


def _tag(segment: Segment, key: str) -> str | None:
    prefix = f"{key}:"
    return next((tag[len(prefix):] for tag in segment.features if tag.startswith(prefix)), None)
