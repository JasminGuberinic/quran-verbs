"""Translate the study site into further languages through a translation memory.

    fil i18n export LANG    write build/i18n/LANG/{meanings,ayah,words,sentences}.tsv + README.txt:
                            only what is still untranslated in LANG, each unique thing once
    fil i18n import LANG    validate the filled sheets; if every line is sound, merge them all
                            (word glosses go to every occurrence), otherwise write nothing
    fil i18n status         per language: how much is translated

Only the translations change on import — the Arabic, the gate's checks and every reader's
verdict are left alone (`service.translate_example`).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fil import example_store, meanings, service, study
from fil import translation_memory as memory
from fil.corpus.parse import iter_segments
from fil.languages import CODES, LANGUAGES, REQUIRED
from fil.resources import AYAH_VERB_GLOSSES_JSON, BUILD_DIR, MEANINGS_JSON, QAC_MORPHOLOGY
from fil.translation_memory import AYAH, MEANINGS, SENTENCES, SHEETS, WORDS, Content, Sheet

OUT = BUILD_DIR / "i18n"
PROBLEMS_SHOWN = 15
TRANSLATED = tuple(code for code in CODES if code not in REQUIRED)   # authored languages need no memory


class UnknownLanguage(ValueError):
    """A language the site does not offer, or one that is authored rather than translated."""


# ---------------------------------------------------------------- commands

def export(language: str, out: Path = OUT) -> dict[Sheet, int]:
    _require_translatable(language)
    folder = out / language
    folder.mkdir(parents=True, exist_ok=True)
    untranslated = memory.missing(load_content(), language)
    for sheet, listed in untranslated.items():
        (folder / sheet.file_name).write_text("".join(map(memory.sheet_line, listed)), encoding="utf-8")
    (folder / "README.txt").write_text(_readme(language), encoding="utf-8")
    counts = {sheet: len(listed) for sheet, listed in untranslated.items()}
    print(f"i18n export {language}: " + ", ".join(f"{sheet.file_name} {count}" for sheet, count in counts.items())
          + f" → {folder}")
    return counts


def import_(language: str, out: Path = OUT) -> bool:
    """Merge the filled sheets — all of them, or nothing at all."""
    _require_translatable(language)
    content = load_content()
    known = memory.entries(content, language)
    folder = out / language
    read = {sheet: _read_filled(folder / sheet.file_name, sheet, known[sheet]) for sheet in SHEETS}
    problems = [problem for _translations, found in read.values() for problem in found]
    if problems:
        _refuse(language, problems)
        return False
    _apply(content, language, {sheet: translations for sheet, (translations, _found) in read.items()})
    return True


def status() -> None:
    content = load_content()
    for language in TRANSLATED:
        listed = memory.entries(content, language)
        print(f"{language}: " + "  ".join(f"{label} {_complete(listed[sheet])}/{len(listed[sheet])}"
                                         for sheet, label in _STATUS_LABELS.items()))


_STATUS_LABELS = {MEANINGS: "meanings", AYAH: "ayah verbs", SENTENCES: "sentences", WORDS: "word glosses"}


def _complete(listed: list[memory.Entry]) -> int:
    return sum(not entry.is_missing for entry in listed)


# ---------------------------------------------------------------- reading the stores

def load_content() -> Content:
    """Every verb with a meaning: its meaning, its example ayah verbs, its shippable sentences."""
    studied = meanings.load()
    authored = _read_store(MEANINGS_JSON)
    return Content(
        meanings={f"{m.root}_{m.form}": authored[f"{m.root}_{m.form}"] for m in studied},
        ayah_verbs=_ayah_verbs(studied),
        sentences=tuple(
            memory.Sentence(m.root, m.form, index, example)
            for m in studied
            for index, example in enumerate(example_store.load(m.root, m.form)) if example.is_shippable
        ),
    )


def _ayah_verbs(studied) -> tuple[memory.AyahVerb, ...]:
    """Each example ayah's highlighted verb that already has its English and Bosnian gloss."""
    glosses = _read_store(AYAH_VERB_GLOSSES_JSON)
    with QAC_MORPHOLOGY.open(encoding="utf-8") as lines:
        ayat = study.ayat_of(study.words_of(iter_segments(lines), service.corpus_corrections()))
    uses = service.form_occurrences()
    found: dict[str, memory.AyahVerb] = {}
    for verb in ((m.root, m.form) for m in studied):
        for example in study.example_ayat(ayat, verb, uses[verb]):
            for word in (w for w in example.words if w.carries(verb)):
                key = f"{word.surah}:{word.ayah}:{word.number}"
                if all(glosses.get(key, {}).get(code) for code in REQUIRED):
                    found.setdefault(key, memory.AyahVerb(key, word.text, glosses[key]))
    return tuple(found.values())


def _read_store(path: Path) -> dict[str, dict[str, str]]:
    """A {key: {language: text}} JSON store, without its `_about`-style notes."""
    return {key: value for key, value in json.loads(path.read_text(encoding="utf-8")).items()
            if not key.startswith("_")}


def _read_filled(path: Path, sheet: Sheet, known: list[memory.Entry]) -> tuple[dict, list[str]]:
    if not path.exists():
        return {}, [f"{sheet.file_name}: missing — run `fil i18n export` first"]
    return memory.read_sheet(sheet, path.read_text(encoding="utf-8").splitlines(), known)


# ---------------------------------------------------------------- writing

def _apply(content: Content, language: str, translations: dict[Sheet, dict]) -> None:
    meanings_merged = _merge_store(MEANINGS_JSON, _by_first_column(translations[MEANINGS]), language)
    ayah_merged = _merge_store(AYAH_VERB_GLOSSES_JSON, _by_first_column(translations[AYAH]), language)
    updates = memory.sentence_updates(content.sentences, _by_first_column(translations[SENTENCES]),
                                      translations[WORDS], language)
    for update in updates:
        sentence = update.sentence
        service.translate_example(sentence.root, sentence.form, sentence.index,
                                  dict(update.translation), [dict(g) for g in update.word_glosses])
    words_applied = sum(bool(g) for update in updates for g in update.word_glosses)
    print(f"i18n import {language}: {meanings_merged} meanings, {ayah_merged} ayah verbs, "
          f"{sum(bool(u.translation) for u in updates)} sentences, {len(translations[WORDS])} word glosses "
          f"applied to {words_applied} occurrences in {len(updates)} sentences")


def _merge_store(path: Path, translations: dict[str, str], language: str) -> int:
    if not translations:
        return 0
    store = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps(memory.merged(store, translations, language), ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8")
    return len(translations)


def _by_first_column(translations: dict[tuple[str, ...], str]) -> dict[str, str]:
    return {key[0]: text for key, text in translations.items()}


def _refuse(language: str, problems: list[str]) -> None:
    print(f"i18n import {language}: REFUSED, nothing written — {len(problems)} problem(s):")
    for problem in problems[:PROBLEMS_SHOWN]:
        print("  " + problem)
    if len(problems) > PROBLEMS_SHOWN:
        print(f"  … and {len(problems) - PROBLEMS_SHOWN} more")


def _require_translatable(language: str) -> None:
    if language not in CODES:
        raise UnknownLanguage(f"{language!r} is not a site language ({', '.join(CODES)})")
    if language in REQUIRED:
        raise UnknownLanguage(f"{language} is authored, not translated through the memory")


def _readme(language: str) -> str:
    name = next(entry.name for entry in LANGUAGES if entry.code == language)
    return _README.format(language=language, name=name)


_README = """\
Translation into {name} ({language}) — Fiʿl, a Quranic Arabic verb trainer
=========================================================================

You are translating learning material for Muslims studying the Arabic of the Quran.
There are four files. Each line is one thing to translate. Fill in ONLY the LAST
column of every line, in {name}.

THE RULES
1. Every line ends with an empty last column, after a TAB. Write your translation there.
2. Do not change, reorder, add or delete any other column or line. Do not add a header.
3. Keep the tabs exactly as they are. Never type a TAB or a line break inside a translation.
4. Fill EVERY line. A file with even one empty last column is refused as a whole and
   nothing is imported — so finish each file completely.
5. Translate from the English column; the Bosnian column is there to help with nuance.
   The Arabic is the source of truth: if English and Arabic seem to differ, follow the Arabic.
6. Use natural, respectful vocabulary as {name}-speaking Muslims actually use it:
   Allah / God and other religious terms (prayer, prophet, messenger, angel, the Hereafter,
   paradise, hellfire, believer, disbeliever, …) in the form usual in Muslim usage of
   {name}, not a Christian or secular rendering. Keep honorific usage natural.
7. Keep the grammar the English shows: tense, person and number ("he said", "they will
   go", "go! (you all)"), and keep it short — these are glosses, not commentary.
   English "you" hides number; the Arabic does not. A 2nd-person PLURAL form (past ـتُمْ,
   present تَـ…ـونَ, command ـُوا as in أَطِيعُوا, "your" as ـكُمْ) must be plural in
   {name} too, even when the English only says "you" — the Bosnian (vi, -te, -ite,
   vaš) shows it.
8. Save the files as UTF-8 plain text with the same names.

THE FILES
- meanings.tsv    root_form  English  Bosnian  [{language}]
    What each verb means, in the dictionary form ("to say"). Several senses: separate with ", ".
- ayah.tsv        surah:ayah:word  Arabic word  English  Bosnian  [{language}]
    One verb in a Quranic verse, translated in context, with its attached pronouns
    ("he said to them"). Translate the English gloss, not the whole verse.
- words.tsv       Arabic word  English gloss  Bosnian gloss  [{language}]
    One word of a practice sentence. Each line is used in EVERY sentence containing
    that word with that meaning, so translate it the way it fits generally ("the man").
- sentences.tsv   id  Arabic sentence  English  Bosnian  [{language}]
    A whole practice sentence, translated naturally as a full sentence.

When done, the files are imported with:  fil i18n import {language}
"""


def _exit_unless(succeeded: bool) -> None:
    if not succeeded:
        raise SystemExit(1)


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[2:]
    commands = {
        "export": lambda: export(args[1]),
        "import": lambda: _exit_unless(import_(args[1])),
        "status": status,
    }
    if not args or args[0] not in commands or (args[0] != "status" and len(args) != 2):
        print(__doc__)
        raise SystemExit(2)
    commands[args[0]]()
