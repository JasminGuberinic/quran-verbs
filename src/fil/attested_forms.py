"""Every form in which the Quran uses a verb, and every ayah it stands in.

A few example ayat show a verb at its clearest; the learner who wants the whole picture
also needs every word the verb takes in the Quran — وَقَالُوٓا۟, فَقَالَ, يَقُولُونَ — and
the ayat themselves. Both are read straight from the corpus (with its documented
corrections already applied), so the counts add up to the verb's own count exactly.

A form is the whole word as it stands in the Quran, clitics and object pronouns
included. Its meaning in context is a gloss: an authored one (data/form_glosses.json,
filled through `fil forms`), or the in-context gloss of an example ayah that holds the
very same word. A form whose letters read two ways (تَقُولُ: "you say" and "she says")
reuses no single in-context gloss — it would be wrong half the time. Until a form has a
gloss, its grammar (tense · mood · person · object) is shown instead, which is never wrong.
A present's mood is the corpus's own tag: subjunctive (MOOD:SUBJ, يَقُولَ), jussive
(MOOD:JUS, يَقُلْ), and indicative (يَقُولُ) wherever it gives none.

Pure: occurrences and texts in, plain values out.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from itertools import groupby

from fil.corpus.oracle import pronoun_key
from fil.corpus.parse import Segment, VerbOccurrence

VerbKey = tuple[str, int]                 # (root, form)
Location = tuple[int, int, int]           # (surah, ayah, word)
Glosses = Mapping[str, Mapping[str, str]]  # key → {language: text}


@dataclass(frozen=True)
class Grammar:
    """How a form is read: who does it, when, and to whom."""

    tense: str
    pronoun: str                 # the subject, as a conjugation pronoun key (huwa, antum…)
    is_passive: bool
    objects: tuple[str, ...]     # attached object pronouns, as pronoun keys (huwa = "him")
    mood: str | None = None      # a present's mood (one of MOODS); None for the past and the command

    def without_mood(self) -> Grammar:
        return replace(self, mood=None)


@dataclass(frozen=True)
class FormOccurrence:
    """One use of a verb: the whole word it stands in, and how that word is read there."""

    location: Location
    text: str
    grammar: Grammar


@dataclass(frozen=True)
class AttestedForm:
    """One distinct word the Quran uses the verb in, with every place it stands."""

    text: str
    locations: tuple[Location, ...]   # in mushaf order
    grammars: tuple[Grammar, ...]     # every reading of these letters, the commonest first

    @property
    def count(self) -> int:
        return len(self.locations)

    @property
    def first(self) -> Location:
        return self.locations[0]

    @property
    def is_ambiguous(self) -> bool:
        # Mood alone does not count: يَقُولُوا۟ after أَن or after لَمْ is still "they say",
        # by the same people, so its in-context gloss still fits.
        return len({grammar.without_mood() for grammar in self.grammars}) > 1


@dataclass(frozen=True)
class VerbAyah:
    """An ayah the verb stands in, and which of its words (by number) hold it."""

    surah: int
    ayah: int
    words: tuple[int, ...]

    @property
    def ref(self) -> str:
        return f"{self.surah}:{self.ayah}"


class UnknownWord(LookupError):
    """An occurrence points at a word the corpus text does not have."""


def word_texts(segments: Iterable[Segment]) -> dict[Location, str]:
    """Every word of the Quran as it is written: its segments joined, clitics and all."""
    return {
        location: "".join(part.surface for part in parts)
        for location, parts in groupby(segments, key=lambda segment: (segment.surah, segment.ayah, segment.word))
    }


def form_occurrences(occurrences: Iterable[VerbOccurrence],
                     word_texts: Mapping[Location, str]) -> dict[VerbKey, tuple[FormOccurrence, ...]]:
    """Every occurrence of every verb, as the whole word it stands in, grouped by verb."""
    grouped: dict[VerbKey, list[FormOccurrence]] = defaultdict(list)
    for occurrence in occurrences:
        location = (occurrence.surah, occurrence.ayah, occurrence.word)
        if location not in word_texts:
            raise UnknownWord(f"{occurrence.root} form {occurrence.form} at {location}: no such word")
        grouped[(occurrence.root, occurrence.form)].append(
            FormOccurrence(location, word_texts[location], grammar_of(occurrence)))
    return {verb: tuple(sorted(found, key=lambda use: use.location)) for verb, found in grouped.items()}


def grammar_of(occurrence: VerbOccurrence) -> Grammar:
    return Grammar(
        tense=occurrence.tense,
        pronoun=pronoun_key((occurrence.person, occurrence.gender, occurrence.number)),
        is_passive=occurrence.passive,
        objects=tuple(pronoun_key(pronoun) for pronoun in occurrence.objects),
        mood=mood_of(occurrence),
    )


MOODS = {"IND": "indicative", "SUBJ": "subjunctive", "JUS": "jussive"}   # corpus tag → our key


class UnknownMood(ValueError):
    """The corpus tags a present with a mood we do not know how to name."""


def mood_of(occurrence: VerbOccurrence) -> str | None:
    """A present's mood; the corpus marks only the subjunctive and the jussive, so the rest are indicative."""
    if occurrence.tense != "present":
        return None
    tag = occurrence.mood or "IND"
    if tag not in MOODS:
        raise UnknownMood(f"{occurrence.surah}:{occurrence.ayah}:{occurrence.word}: MOOD:{tag}")
    return MOODS[tag]


def grammar_view(grammar: Grammar) -> dict:
    """A reading as the page data carries it (site/ayat.js and fil.pages.render label it)."""
    view = {"tense": grammar.tense, "pronoun": grammar.pronoun, "passive": grammar.is_passive,
            "objects": list(grammar.objects)}
    return {**view, "mood": grammar.mood} if grammar.mood else view


def attested_forms(uses: Sequence[FormOccurrence]) -> list[AttestedForm]:
    """One entry per distinct word, the most frequent first; ties go to the earlier one."""
    by_text: dict[str, list[FormOccurrence]] = defaultdict(list)
    for use in sorted(uses, key=lambda use: use.location):
        by_text[use.text].append(use)
    forms = [_form(text, found) for text, found in by_text.items()]
    return sorted(forms, key=lambda form: (-form.count, form.first))


def _form(text: str, uses: list[FormOccurrence]) -> AttestedForm:
    readings = Counter(use.grammar for use in uses)
    first_seen = {use.grammar: index for index, use in reversed(list(enumerate(uses)))}
    grammars = sorted(readings, key=lambda grammar: (-readings[grammar], first_seen[grammar]))
    return AttestedForm(text, tuple(use.location for use in uses), tuple(grammars))


def verb_ayat(uses: Iterable[FormOccurrence]) -> list[VerbAyah]:
    """Every ayah the verb stands in, once, in mushaf order, with the words that hold it."""
    words: dict[tuple[int, int], set[int]] = defaultdict(set)
    for use in uses:
        surah, ayah, word = use.location
        words[(surah, ayah)].add(word)
    return [VerbAyah(surah, ayah, tuple(sorted(found))) for (surah, ayah), found in sorted(words.items())]


# ---------------------------------------------------------------- glosses

def form_key(verb: VerbKey, text: str) -> str:
    """How a form is named in data/form_glosses.json and in the gloss sheets."""
    root, form = verb
    return f"{root}|{form}|{text}"


def location_key(location: Location) -> str:
    """How a word is named in data/ayah_verb_glosses.json."""
    return ":".join(map(str, location))


def gloss_of(verb: VerbKey, form: AttestedForm, authored: Glosses, in_context: Glosses) -> dict[str, str]:
    """{language: gloss} for a form: authored first, else an example ayah's gloss of the same word."""
    reused = {} if form.is_ambiguous else _first_in_context(form, in_context)
    return {**reused, **authored.get(form_key(verb, form.text), {})}


def _first_in_context(form: AttestedForm, in_context: Glosses) -> Mapping[str, str]:
    return next((in_context[key] for key in map(location_key, form.locations) if key in in_context), {})
