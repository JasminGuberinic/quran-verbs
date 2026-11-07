"""Gloss every Quranic form of the studied verbs — each distinct word once per language.

    fil forms status          how many forms are glossed, per active language
    fil forms export LANG     build/forms/LANG/forms.tsv: the forms still without a LANG gloss
    fil forms import LANG     check the filled sheet; if every line is sound, merge it into
                              data/form_glosses.json — all of it, or nothing

A verb page lists every word the Quran uses the verb in (fil.attested_forms). A form shows
its gloss when it has one — authored here, or the in-context gloss of an example ayah that
holds the very same word — and its grammar until then. English and Bosnian are written
from the Arabic (the sheet gives its grammar and the first ayah it stands in); every
other language translates them, like the rest of the translation memory (fil i18n).
"""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from pathlib import Path

from fil import attested_forms, meanings, service
from fil import translation_memory as memory
from fil.attested_forms import AttestedForm, VerbKey
from fil.ayah_translations import AyahTranslations
from fil.languages import CODES
from fil.pages import interface_text
from fil.pages.render import grammar_label
from fil.resources import AYAH_VERB_GLOSSES_JSON, BUILD_DIR, COMPOSED_FORM_GLOSSES_JSON, FORM_GLOSSES_JSON
from fil.translation_memory import FormToGloss

OUT = BUILD_DIR / "forms"
ACTIVE = ("bs", "en", "tr", "fr", "id", "ur", "bn", "fa")   # the languages glossed first
PROBLEMS_SHOWN = 15


class UnknownLanguage(ValueError):
    """A language the site does not offer."""


# ---------------------------------------------------------------- commands

def status() -> None:
    forms = forms_to_gloss()
    glossed = " · ".join(f"{code} {sum(bool(form.glosses.get(code)) for form in forms)}" for code in ACTIVE)
    print(f"{len(forms)} distinct forms; glossed: {glossed}")


def export(language: str, out: Path = OUT) -> int:
    _require_known(language)
    missing = [entry for entry in memory.form_entries(forms_to_gloss(), language) if entry.is_missing]
    folder = out / language
    folder.mkdir(parents=True, exist_ok=True)
    (folder / memory.form_sheet(language).file_name).write_text("".join(map(memory.sheet_line, missing)), encoding="utf-8")
    print(f"forms export {language}: {len(missing)} forms to gloss → {folder}")
    return len(missing)


def import_(language: str, out: Path = OUT) -> bool:
    """Merge the filled sheet — every line of it, or nothing."""
    _require_known(language)
    sheet = memory.form_sheet(language)
    path = out / language / sheet.file_name
    if not path.exists():
        print(f"forms import {language}: {path} is missing — run `fil forms export {language}` first")
        return False
    known = memory.form_entries(forms_to_gloss(), language)
    glosses, problems = memory.read_sheet(sheet, path.read_text(encoding="utf-8").splitlines(), known)
    if problems:
        _refuse(language, problems)
        return False
    store = json.loads(FORM_GLOSSES_JSON.read_text(encoding="utf-8"))
    merged = memory.merged(store, {key[0]: text for key, text in glosses.items()}, language)
    FORM_GLOSSES_JSON.write_text(json.dumps(merged, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"forms import {language}: {len(glosses)} glosses merged into {FORM_GLOSSES_JSON.name}")
    return True


# ---------------------------------------------------------------- what there is to gloss

def studied_forms() -> list[tuple[VerbKey, AttestedForm]]:
    """Every distinct form of every studied verb, verb by verb, the most frequent first."""
    uses = service.form_occurrences()
    return [((m.root, m.form), form) for m in meanings.load()
            for form in attested_forms.attested_forms(uses[(m.root, m.form)])]


def read_glosses() -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    """(form glosses, example ayah glosses): the two places a form's gloss comes from.

    Form glosses are the authored ones over the composed ones (fil compose), language by
    language: a composed form keeps its English and Bosnian when only its translations into
    other languages are authored. A form is composed only while it has no complete authored
    or in-context gloss, so a composed gloss never stands in front of a written one.
    """
    composed, authored = read_store(COMPOSED_FORM_GLOSSES_JSON), read_store(FORM_GLOSSES_JSON)
    merged = {key: {**composed.get(key, {}), **authored.get(key, {})} for key in composed.keys() | authored.keys()}
    return merged, read_store(AYAH_VERB_GLOSSES_JSON)


def forms_to_gloss() -> list[FormToGloss]:
    english = interface_text.load()["en"]
    authored, in_context = read_glosses()
    lemmas = {(verb.root, verb.form): verb.lemma for verb in service.list_verbs()}
    meaning = {(m.root, m.form): dict(m.glosses)["en"] for m in meanings.load()}
    translations = AyahTranslations()
    return [
        FormToGloss(
            key=attested_forms.form_key(verb, form.text), arabic=form.text,
            verb=f"{lemmas[verb]} {meaning[verb]}",
            grammar=grammar_label([attested_forms.grammar_view(g) for g in form.grammars], english),
            first_ayah=_first_ayah(form, translations),
            glosses=attested_forms.gloss_of(verb, form, authored, in_context),
        )
        for verb, form in studied_forms()
    ]


def _first_ayah(form: AttestedForm, translations: AyahTranslations) -> str:
    surah, ayah, _word = form.first
    english = translations.of(surah, ayah).get("en", {}).get("text", "")
    return f"{surah}:{ayah} {' '.join(english.split())}"


def read_store(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    stored: Mapping[str, dict[str, str]] = json.loads(path.read_text(encoding="utf-8"))
    return {key: value for key, value in stored.items() if not key.startswith("_")}


def _require_known(language: str) -> None:
    if language not in CODES:
        raise UnknownLanguage(f"{language!r} is not a site language ({', '.join(CODES)})")


def _refuse(language: str, problems: list[str]) -> None:
    print(f"forms import {language}: REFUSED, nothing written — {len(problems)} problem(s):")
    for problem in problems[:PROBLEMS_SHOWN]:
        print("  " + problem)
    if len(problems) > PROBLEMS_SHOWN:
        print(f"  … and {len(problems) - PROBLEMS_SHOWN} more")


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[2:]
    commands = {
        "status": status,
        "export": lambda: export(args[1]),
        "import": lambda: _exit_unless(import_(args[1])),
    }
    if not args or args[0] not in commands or (args[0] != "status" and len(args) != 2):
        print(__doc__)
        raise SystemExit(2)
    commands[args[0]]()


def _exit_unless(succeeded: bool) -> None:
    if not succeeded:
        raise SystemExit(1)

