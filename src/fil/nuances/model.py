"""What a group of Quranic near-synonyms is, read from data/nuance_groups.json and validated.

Pure data. A group has a page slug, a title, what its words share and how to tell them
apart; each member is one Quranic word with its corpus identity — a verb of the catalogue
("جيأ_1") or one or more noun-catalogue lemmas ("رَجُل|رجل", "رِجال|رجل": the corpus files a
broken plural under a lemma of its own) — its Quranic count, its nuance, and the ayat that
illustrate it. Every learner-facing text is written in Bosnian and English; nothing that
fails these rules is ever built (InvalidNuanceData names what is wrong).
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

LANGUAGES = ("bs", "en")
MIN_MEMBERS = 2
MIN_AYAT, MAX_AYAT = 1, 3
_SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_VERB_KEY = re.compile(r"^(\S+)_([1-9]|10)$")
_REFERENCE = re.compile(r"^(\d{1,3}):(\d{1,3})$")


class InvalidNuanceData(ValueError):
    """A stored nuance group that must not reach a learner; the message names what is wrong."""


@dataclass(frozen=True)
class Text:
    """One learner-facing text, in every language the section is written in."""

    bs: str
    en: str

    def in_language(self, code: str) -> str:
        return self.bs if code == "bs" else self.en


@dataclass(frozen=True)
class Illustration:
    """An ayah that shows why the word was chosen there."""

    surah: int
    ayah: int
    why: Text

    @property
    def reference(self) -> str:
        return f"{self.surah}:{self.ayah}"


@dataclass(frozen=True)
class CorpusWord:
    """Who a member is in the corpus: a catalogue verb (root, form), or noun-catalogue lemmas."""

    verb: tuple[str, int] | None = None
    lemmas: tuple[tuple[str, str], ...] = ()     # (lemma, root)

    @property
    def is_verb(self) -> bool:
        return self.verb is not None

    @property
    def verb_key(self) -> str | None:
        """The verb pages' key, "جيأ_1"."""
        return f"{self.verb[0]}_{self.verb[1]}" if self.verb else None

    @property
    def lemma_keys(self) -> tuple[str, ...]:
        """The noun and adjective cards' keys, "رَجُل|رجل"."""
        return tuple(f"{lemma}|{root}" for lemma, root in self.lemmas)

    def describe(self) -> str:
        return self.verb_key or ", ".join(self.lemma_keys)


@dataclass(frozen=True)
class NuanceMember:
    arabic: str                  # with harakat, as the page heads it: إِنْسَان
    corpus: CorpusWord
    count: int                   # how often the Quran uses it, as the corpus counts it
    meaning: Text
    nuance: Text
    ayat: tuple[Illustration, ...]
    # How the headword is voiced, where that differs from how it is shown: a pausal tāʾ marbūṭa
    # (خَشْيَة) the two readers of fil.speech disagree on is said as its citation form (خَشْيَةٌ).
    spoken: str | None = None

    @property
    def said(self) -> str:
        return self.spoken or self.arabic


@dataclass(frozen=True)
class NuanceGroup:
    slug: str
    title: Text
    shared: Text                 # what the words have in common
    tell_apart: Text             # the one-line summary: how to tell them apart
    sources: tuple[str, ...]     # the classical works each claim rests on, by name
    notes: tuple[str, ...]       # decisions taken, for the reviewer and the next batch
    members: tuple[NuanceMember, ...]

    @property
    def cited_ayat(self) -> tuple[tuple[NuanceMember, Illustration], ...]:
        return tuple((member, illustration) for member in self.members for illustration in member.ayat)


# ---------------------------------------------------------------- parsing

def parse_groups(entries: Mapping[str, Mapping]) -> tuple[NuanceGroup, ...]:
    """Every group, validated; the first problem stops the load with what and where."""
    return tuple(parse_group(slug, entry) for slug, entry in entries.items())


def parse_group(slug: str, entry: Mapping) -> NuanceGroup:
    if not _SLUG.match(slug):
        raise InvalidNuanceData(f"{slug!r}: a group's key is its page slug — lowercase latin letters, digits, hyphens")
    members = tuple(_member(slug, index, item) for index, item in enumerate(_required(slug, entry, "members"), 1))
    if len(members) < MIN_MEMBERS:
        raise InvalidNuanceData(f"{slug}: a group needs at least {MIN_MEMBERS} members, has {len(members)}")
    _refuse_duplicates(slug, [member.arabic for member in members], "member")
    sources = tuple(_required(slug, entry, "sources"))
    if not sources or not all(isinstance(source, str) and source.strip() for source in sources):
        raise InvalidNuanceData(f"{slug}: name the classical works the group rests on in `sources`")
    return NuanceGroup(slug=slug, title=_text(slug, entry, "title"), shared=_text(slug, entry, "shared"),
                       tell_apart=_text(slug, entry, "tellApart"), sources=sources,
                       notes=tuple(entry.get("notes", ())), members=members)


def _member(slug: str, index: int, entry: Mapping) -> NuanceMember:
    where = f"{slug} member {index}"
    arabic = _required(where, entry, "arabic")
    where = f"{slug} {arabic}"
    count = _required(where, entry, "count")
    if not isinstance(count, int) or count < 1:
        raise InvalidNuanceData(f"{where}: `count` must be the corpus's count, a positive whole number")
    ayat = tuple(_illustration(where, item) for item in _required(where, entry, "ayat"))
    if not MIN_AYAT <= len(ayat) <= MAX_AYAT:
        raise InvalidNuanceData(f"{where}: cite {MIN_AYAT}–{MAX_AYAT} illustrating ayat, not {len(ayat)}")
    _refuse_duplicates(where, [illustration.reference for illustration in ayat], "ayah")
    return NuanceMember(arabic=arabic, corpus=_corpus_word(where, entry), count=count,
                        meaning=_text(where, entry, "meaning"), nuance=_text(where, entry, "nuance"), ayat=ayat,
                        spoken=_spoken(where, entry))


def _spoken(where: str, entry: Mapping) -> str | None:
    spoken = entry.get("spoken")
    if spoken is not None and (not isinstance(spoken, str) or not spoken.strip()):
        raise InvalidNuanceData(f"{where}: `spoken` is the headword as voiced — leave it out or write it")
    return spoken


def _corpus_word(where: str, entry: Mapping) -> CorpusWord:
    """Exactly one of `verb` ("جيأ_1") or `lemmas` (["رَجُل|رجل", ...])."""
    verb, lemmas = entry.get("verb"), entry.get("lemmas")
    if bool(verb) == bool(lemmas):
        raise InvalidNuanceData(f"{where}: give exactly one of `verb` (root_form) or `lemmas` (lemma|root, ...)")
    if verb:
        found = _VERB_KEY.match(verb)
        if not found:
            raise InvalidNuanceData(f"{where}: `verb` {verb!r} is not root_form, e.g. جيأ_1")
        return CorpusWord(verb=(found.group(1), int(found.group(2))))
    pairs = tuple(tuple(key.split("|")) for key in lemmas)
    if any(len(pair) != 2 or not all(pair) for pair in pairs):
        raise InvalidNuanceData(f"{where}: each of `lemmas` is lemma|root, got {lemmas}")
    _refuse_duplicates(where, list(lemmas), "lemma")
    return CorpusWord(lemmas=pairs)


def _illustration(where: str, entry: Mapping) -> Illustration:
    reference = _required(where, entry, "ref")
    found = _REFERENCE.match(reference)
    if not found:
        raise InvalidNuanceData(f"{where}: {reference!r} is not an ayah reference surah:ayah")
    return Illustration(int(found.group(1)), int(found.group(2)), _text(f"{where} {reference}", entry, "why"))


def _text(where: str, entry: Mapping, field: str) -> Text:
    """A learner-facing text: present and non-empty in every language."""
    value = _required(where, entry, field)
    missing = [code for code in LANGUAGES if not isinstance(value, Mapping) or not str(value.get(code, "")).strip()]
    if missing:
        raise InvalidNuanceData(f"{where}: `{field}` has no {' or '.join(missing)} text")
    return Text(bs=value["bs"].strip(), en=value["en"].strip())


def _required(where: str, entry: Mapping, field: str):
    if field not in entry:
        raise InvalidNuanceData(f"{where}: `{field}` is missing")
    return entry[field]


def _refuse_duplicates(where: str, values: Sequence[str], what: str) -> None:
    repeated = sorted({value for value in values if values.count(value) > 1})
    if repeated:
        raise InvalidNuanceData(f"{where}: the same {what} twice: {repeated}")

