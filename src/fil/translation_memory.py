"""A translation memory: each unique piece of content is translated once per language.

The study site is authored in English and Bosnian. Every further language is filled in
bulk, from four compact sheets a translator completes by adding one column:

    meanings.tsv    root_form   en  bs              → what each verb means
    ayah.tsv        s:a:w   arabic  en  bs          → each example ayah's verb, in context
    words.tsv       arabic  en  bs                  → one word gloss, reused everywhere
    sentences.tsv   root|form|index arabic en bs    → one practice sentence

`words.tsv` is the memory proper: اللَّهُ = God appears in hundreds of sentences but is
listed (and paid for) once; its translation is applied to every occurrence on import.

This module is pure: it decides what a sheet holds and whether a filled sheet may be
trusted. Reading the stores and writing the files is the `fil i18n` stage's job.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from fil.examples import Example
from fil.languages import CODES, REQUIRED

WordKey = tuple[str, str]   # (arabic, en): the same word with another meaning is another entry


@dataclass(frozen=True)
class Sheet:
    """One translation file: reference columns a translator reads, then one to fill."""

    file_name: str
    columns: tuple[str, ...]   # the reference columns, in order
    key_width: int = 1         # how many leading columns identify an entry

    @property
    def width(self) -> int:
        return len(self.columns) + 1

    def key_of(self, reference: tuple[str, ...]) -> tuple[str, ...]:
        return reference[:self.key_width]


MEANINGS = Sheet("meanings.tsv", ("root_form", "en", "bs"))
AYAH = Sheet("ayah.tsv", ("surah:ayah:word", "arabic", "en", "bs"))
WORDS = Sheet("words.tsv", ("arabic", "en", "bs"), key_width=2)
SENTENCES = Sheet("sentences.tsv", ("root|form|index", "arabic", "en", "bs"))
SHEETS: tuple[Sheet, ...] = (MEANINGS, AYAH, WORDS, SENTENCES)

# Every Quranic form of a verb, glossed once (fil forms). English and Bosnian are written from
# the Arabic, its grammar and the first ayah it stands in; the other languages translate them.
FORMS_AUTHORED = Sheet("forms.tsv", ("root|form|arabic", "arabic", "verb", "grammar", "first ayah"))
FORMS_TRANSLATED = Sheet("forms.tsv", ("root|form|arabic", "arabic", "grammar", "en", "bs"))


@dataclass(frozen=True)
class AyahVerb:
    key: str                         # surah:ayah:word
    arabic: str
    glosses: Mapping[str, str]       # language → in-context translation


@dataclass(frozen=True)
class Sentence:
    root: str
    form: int
    index: int                       # position in the verb's stored sentences
    example: Example

    @property
    def id(self) -> str:
        return f"{self.root}|{self.form}|{self.index}"


@dataclass(frozen=True)
class FormToGloss:
    """One distinct Quranic form of a verb, with what a glosser needs to read it right."""

    key: str                         # root|form|arabic (fil.attested_forms.form_key)
    arabic: str
    verb: str                        # the verb and its meaning, e.g. "قَالَ to say"
    grammar: str                     # its grammar, in English
    first_ayah: str                  # where it first stands, with that ayah in English
    glosses: Mapping[str, str]       # language → gloss, as far as it has one


@dataclass(frozen=True)
class Content:
    """Everything a learner reads that needs translating."""

    meanings: Mapping[str, Mapping[str, str]]   # root_form → language → meaning
    ayah_verbs: tuple[AyahVerb, ...]
    sentences: tuple[Sentence, ...]


@dataclass(frozen=True)
class Entry:
    reference: tuple[str, ...]
    translation: str                 # the text already held in the language, "" if none

    @property
    def is_missing(self) -> bool:
        return not self.translation


@dataclass(frozen=True)
class SentenceUpdate:
    """What `service.translate_example` must add to one sentence."""

    sentence: Sentence
    translation: Mapping[str, str]             # {language: text}, or {} to leave it
    word_glosses: tuple[Mapping[str, str], ...]  # one per word, {} where nothing changes


class UnsafeCell(ValueError):
    """Content that would break the sheet's tab-separated shape."""


# ---------------------------------------------------------------- what a sheet holds

def entries(content: Content, language: str) -> dict[Sheet, list[Entry]]:
    """Every entry of every sheet, translated or not, for one language."""
    return {
        MEANINGS: _meaning_entries(content.meanings, language),
        AYAH: [_entry((verb.key, verb.arabic, verb.glosses["en"], verb.glosses["bs"]), verb.glosses.get(language, ""))
               for verb in content.ayah_verbs],
        WORDS: _word_entries(content.sentences, language),
        SENTENCES: [_entry((s.id, s.example.arabic, s.example.en, s.example.bs),
                           dict(s.example.translations).get(language, ""))
                    for s in content.sentences],
    }


def form_sheet(language: str) -> Sheet:
    return FORMS_AUTHORED if language in REQUIRED else FORMS_TRANSLATED


def form_entries(forms: Iterable[FormToGloss], language: str) -> list[Entry]:
    """Every form's entry in one language; a translated language only gets forms glossed in en and bs."""
    if language in REQUIRED:
        return [_entry((form.key, form.arabic, form.verb, form.grammar, form.first_ayah), form.glosses.get(language, ""))
                for form in forms]
    return [_entry((form.key, form.arabic, form.grammar, form.glosses["en"], form.glosses["bs"]),
                   form.glosses.get(language, ""))
            for form in forms if all(form.glosses.get(code) for code in REQUIRED)]


def missing(content: Content, language: str) -> dict[Sheet, list[Entry]]:
    """Only what is still untranslated — what a translator is given."""
    return {sheet: [entry for entry in listed if entry.is_missing]
            for sheet, listed in entries(content, language).items()}


def sheet_line(entry: Entry) -> str:
    """The entry as a line to fill: its reference columns and an empty last one."""
    return "\t".join(entry.reference) + "\t\n"


def _meaning_entries(meanings: Mapping[str, Mapping[str, str]], language: str) -> list[Entry]:
    return [_entry((key, glosses["en"], glosses["bs"]), glosses.get(language, ""))
            for key, glosses in meanings.items()]


def _word_entries(sentences: Iterable[Sentence], language: str) -> list[Entry]:
    """One entry per unique (arabic, en) word; translated only once every occurrence is."""
    first: dict[WordKey, Entry] = {}
    translated_everywhere: dict[WordKey, bool] = {}
    for sentence in sentences:
        for word in sentence.example.words:
            key = (word.arabic, word.en)
            translation = dict(word.translations).get(language, "")
            first.setdefault(key, _entry((word.arabic, word.en, word.bs), translation))
            translated_everywhere[key] = translated_everywhere.get(key, True) and bool(translation)
    return [entry if translated_everywhere[key] else Entry(entry.reference, "")
            for key, entry in first.items()]


def _entry(reference: tuple[str, ...], translation: str) -> Entry:
    unsafe = [cell for cell in reference if "\t" in cell or "\n" in cell]
    if unsafe:
        raise UnsafeCell(f"a tab or newline inside {unsafe[0]!r} would corrupt the sheet")
    return Entry(tuple(cell.strip() for cell in reference), translation.strip())


# ---------------------------------------------------------------- reading a filled sheet

def read_sheet(sheet: Sheet, lines: Iterable[str], known: Iterable[Entry]) -> tuple[dict[tuple[str, ...], str], list[str]]:
    """A filled sheet → ({key: translation}, problems). Any problem means: trust none of it."""
    expected = {sheet.key_of(entry.reference): entry.reference for entry in known}
    translations: dict[tuple[str, ...], str] = {}
    problems: list[str] = []
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        where = f"{sheet.file_name}:{number}"
        problem, key, translation = _read_line(sheet, line, expected)
        if not problem and key in translations:
            problem = f"{_shown(key)} is listed twice"
        if problem:
            problems.append(f"{where}: {problem}")
            continue
        translations[key] = translation
    return translations, problems


def _read_line(sheet: Sheet, line: str, expected: Mapping[tuple[str, ...], tuple[str, ...]]) -> tuple[str, tuple[str, ...], str]:
    columns = line.rstrip("\r\n").split("\t")
    if len(columns) != sheet.width:
        return f"expected {sheet.width} tab-separated columns, got {len(columns)}", (), ""
    reference, translation = tuple(cell.strip() for cell in columns[:-1]), columns[-1].strip()
    key = sheet.key_of(reference)
    if key not in expected:
        return f"unknown {sheet.columns[0]} {_shown(key)}", key, ""
    if reference != expected[key]:
        return "a reference column was changed — only the last column may be filled", key, ""
    if not translation:
        return "the last column is empty", key, ""
    return "", key, translation


def _shown(key: tuple[str, ...]) -> str:
    return " / ".join(key)


# ---------------------------------------------------------------- applying the memory

def merged(store: Mapping[str, object], translations: Mapping[str, str], language: str) -> dict[str, object]:
    """A {key: {language: text}} store with `language` set for the given keys.

    Untouched entries (and notes such as `_about`) are kept as they are; languages are
    kept in the site's language order, so a merge reads as one added line per entry.
    """
    result = dict(store)
    for key, text in translations.items():
        result[key] = _in_language_order({**store.get(key, {}), language: text})
    return result


def _in_language_order(glosses: Mapping[str, str]) -> dict[str, str]:
    known = [code for code in CODES if code in glosses]
    return {**{code: glosses[code] for code in known}, **{k: v for k, v in glosses.items() if k not in CODES}}


def sentence_updates(sentences: Iterable[Sentence], sentence_translations: Mapping[str, str],
                     word_memory: Mapping[WordKey, str], language: str) -> list[SentenceUpdate]:
    """What changes in each sentence: its own translation, and every word the memory knows."""
    updates = (_update_for(sentence, sentence_translations, word_memory, language) for sentence in sentences)
    return [update for update in updates if update is not None]


def _update_for(sentence: Sentence, sentence_translations: Mapping[str, str],
                word_memory: Mapping[WordKey, str], language: str) -> SentenceUpdate | None:
    example = sentence.example
    translation = _changed(dict(example.translations), sentence_translations.get(sentence.id), language)
    word_glosses = tuple(_changed(dict(word.translations), word_memory.get((word.arabic, word.en)), language)
                         for word in example.words)
    if not translation and not any(word_glosses):
        return None
    return SentenceUpdate(sentence, translation, word_glosses)


def _changed(existing: Mapping[str, str], text: str | None, language: str) -> dict[str, str]:
    return {language: text} if text and existing.get(language) != text else {}
