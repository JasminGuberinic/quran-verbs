"""Gloss the remaining Quranic forms by composition: proclitics + verb cell + object.

    fil compose status               what composition would gloss now, and why the rest are skipped
    fil compose sheets DIR [PER]     DIR/<n>/cells.tsv: the Bosnian paradigm cells still to write, PER verbs a sheet
    fil compose paradigms DIR        check every filled DIR/*/cells.tsv; merge into data/bs_paradigms.json — all or nothing
    fil compose build                write data/composed_form_glosses.json (English and Bosnian)
    fil compose sample N OUT [SEED]  a random sample of composed glosses for a blind review

Only forms without a gloss are composed: an authored gloss or an example ayah's own gloss
always wins (see fil.attested_forms.gloss_of and fil.stages.forms.read_glosses).
"""

from __future__ import annotations

import json
import random
import sys
from functools import lru_cache
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from fil import attested_forms, meanings, service
from fil.attested_forms import AttestedForm, VerbKey
from fil.ayah_translations import AyahTranslations
from fil.composition import english
from fil.composition.compose import Composed, Reading, Skipped, compose, plan
from fil.composition.decomposition import CannotCompose
from fil.composition.english import EnglishVerb
from fil.composition.paradigms import SHEET_COLUMNS, InvalidParadigm, from_sheet, validated, verb_key
from fil.resources import (AYAH_VERB_GLOSSES_JSON, BS_PARADIGMS_JSON, COMPOSED_FORM_GLOSSES_JSON, FORM_GLOSSES_JSON,
                           POLYSEMOUS_VERBS_JSON)
from fil.stages import forms

SHEET = "cells.tsv"
VERBS_PER_SHEET = 100
_ABOUT_GLOSSES = ("Quranic forms glossed by rule, not by hand: proclitic words + the verb's cell (English "
                  "conjugated from data/meanings.json, Bosnian from data/bs_paradigms.json) + its object. "
                  "Key: root|form|arabic. Only forms without an authored or in-context gloss; written by "
                  "`fil compose build` — regenerate rather than edit.")
_ABOUT_PARADIGMS = ("Per verb (root|form), the Bosnian of each cell the Quran uses it in: tense|voice|subject|objects "
                    "→ the cell as it opens a sentence. Filled through `fil compose sheets/paradigms`.")


@dataclass(frozen=True)
class Candidate:
    """A form still without a gloss, with what composing it needs."""

    verb: VerbKey
    form: AttestedForm
    readings: tuple[Reading, ...]
    meaning_en: str
    meaning_bs: str

    @property
    def key(self) -> str:
        return verb_key(*self.verb)


# ---------------------------------------------------------------- commands

def status() -> None:
    paradigms = _paradigms()
    _report([(candidate, _composed(candidate, paradigms)) for candidate in candidates()])


def build() -> None:
    paradigms = _paradigms()
    results = [(candidate, _composed(candidate, paradigms)) for candidate in candidates()]
    glosses = {attested_forms.form_key(candidate.verb, candidate.form.text): {"en": result.en, "bs": result.bs}
               for candidate, result in results if isinstance(result, Composed)}
    _write_json(COMPOSED_FORM_GLOSSES_JSON, {"_about": _ABOUT_GLOSSES, **dict(sorted(glosses.items()))})
    _report(results)


def sheets(out: Path, per_sheet: int = VERBS_PER_SHEET) -> None:
    """About PER verbs a sheet, each sheet as long as the next, listing every cell a
    composable form needs and no paradigm has yet."""
    rows = _needed_rows(_paradigms())
    verbs = list(dict.fromkeys(row[0] for row in rows))
    for number, batch in enumerate(_balanced(rows, -(-len(verbs) // per_sheet)), 1):
        folder = out / str(number)
        folder.mkdir(parents=True, exist_ok=True)
        lines = ["\t".join(SHEET_COLUMNS)] + ["\t".join(row) for row in rows if row[0] in batch]
        (folder / SHEET).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"compose sheets: {len(rows)} cells of {len(verbs)} verbs → {out}/<n>/{SHEET}")


def _balanced(rows: list[tuple[str, ...]], sheet_count: int) -> list[set[str]]:
    """Verbs split into `sheet_count` groups of about the same number of cells, whole verbs only."""
    cells = Counter(row[0] for row in rows)
    target = -(-len(rows) // max(sheet_count, 1))
    groups: list[set[str]] = [set()]
    filled = 0
    for verb, count in cells.items():
        if filled >= target:
            groups.append(set())
            filled = 0
        groups[-1].add(verb)
        filled += count
    return groups


def import_paradigms(folder: Path) -> bool:
    try:
        filled = [from_sheet(path.read_text(encoding="utf-8").splitlines()) for path in sorted(folder.glob(f"*/{SHEET}"))]
    except InvalidParadigm as problem:
        print(f"compose paradigms: REFUSED, nothing written — {str(problem)[:2000]}")
        return False
    merged = {verb: dict(cells) for verb, cells in _paradigms().items()}
    for sheet in filled:
        for verb, cells in sheet.items():
            merged.setdefault(verb, {}).update(cells)
    _write_json(BS_PARADIGMS_JSON, {"_about": _ABOUT_PARADIGMS, **validated(dict(sorted(merged.items())))})
    print(f"compose paradigms: {sum(map(len, filled))} verbs from {len(filled)} sheets → {BS_PARADIGMS_JSON.name}")
    return True


def sample(size: int, out: Path, seed: int = 1) -> None:
    """Arabic form, its first ayah and both glosses — no code, no rule — for a blind reviewer."""
    composed = _read(COMPOSED_FORM_GLOSSES_JSON)
    by_key = {attested_forms.form_key(candidate.verb, candidate.form.text): candidate for candidate in candidates(every=True)}
    chosen = random.Random(seed).sample(sorted(composed), min(size, len(composed)))
    translations = AyahTranslations()
    lines = ["id\tarabic\tayah\tayah_english\tverb_meaning\ten\tbs"]
    for number, key in enumerate(chosen, 1):
        candidate = by_key[key]
        surah, ayah, word = candidate.form.first
        ayah_english = " ".join(translations.of(surah, ayah).get("en", {}).get("text", "").split())
        lines.append("\t".join((str(number), candidate.form.text, f"{surah}:{ayah} (word {word})", ayah_english,
                                candidate.meaning_en, composed[key]["en"], composed[key]["bs"])))
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"compose sample: {len(chosen)} glosses → {out}")


# ---------------------------------------------------------------- what there is to compose

def candidates(every: bool = False) -> list[Candidate]:
    """Every studied form still without an authored or in-context gloss (`every`: glossed ones too)."""
    authored = forms.read_store(FORM_GLOSSES_JSON)
    in_context = forms.read_store(AYAH_VERB_GLOSSES_JSON)
    readings = service.verb_readings()
    meaning = {(m.root, m.form): m for m in meanings.load()}
    return [
        Candidate(verb, form, tuple(readings[verb][location] for location in form.locations),
                  meaning[verb].gloss("en"), meaning[verb].gloss("bs"))
        for verb, form in forms.studied_forms()
        if every or not attested_forms.is_complete(attested_forms.gloss_of(verb, form, authored, in_context))
    ]


def _composed(candidate: Candidate, paradigms: dict) -> Composed | Skipped:
    return compose(candidate.key, candidate.form, candidate.readings, candidate.meaning_en,
                   paradigms.get(candidate.key, {}), _polysemous())


def _needed_rows(paradigms: dict) -> list[tuple[str, ...]]:
    rows: dict[tuple[str, str], tuple[str, ...]] = {}
    lemmas = {(verb.root, verb.form): verb.lemma for verb in service.list_verbs()}
    for candidate in candidates():
        try:
            planned = plan(candidate.key, candidate.form, candidate.readings, candidate.meaning_en, _polysemous())
        except CannotCompose:
            continue
        cell = planned.decomposition.cell
        if cell.code in paradigms.get(candidate.key, {}) or (candidate.key, cell.code) in rows:
            continue
        hint = english.cell_gloss(cell, EnglishVerb.from_meaning(candidate.meaning_en))
        rows[(candidate.key, cell.code)] = (candidate.key, lemmas[candidate.verb], candidate.meaning_en,
                                            candidate.meaning_bs, cell.code, hint, candidate.form.text, "")
    return list(rows.values())


def _report(results: list[tuple[Candidate, Composed | Skipped]]) -> None:
    reasons = Counter(result.reason for _candidate, result in results if isinstance(result, Skipped))
    composed = sum(isinstance(result, Composed) for _candidate, result in results)
    print(f"compose: {len(results)} unglossed forms; composed {composed}; skipped {sum(reasons.values())}")
    for reason, count in reasons.most_common():
        print(f"  {count:5}  {reason}")


@lru_cache(maxsize=1)
def _polysemous() -> frozenset[str]:
    """Verbs whose first sense misleads in too many ayat (data/polysemous_verbs.json: verb → its other senses)."""
    return frozenset(_read(POLYSEMOUS_VERBS_JSON))


def _paradigms() -> dict[str, dict[str, str]]:
    return validated(_read(BS_PARADIGMS_JSON))


def _read(path: Path) -> dict:
    if not path.exists():
        return {}
    return {key: value for key, value in json.loads(path.read_text(encoding="utf-8")).items() if not key.startswith("_")}


def _write_json(path: Path, content: dict) -> None:
    path.write_text(json.dumps(content, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[2:]
    commands = {
        "status": (0, lambda: status()),
        "build": (0, lambda: build()),
        "sheets": (1, lambda: sheets(Path(args[1]), *map(int, args[2:3]))),
        "paradigms": (1, lambda: _exit_unless(import_paradigms(Path(args[1])))),
        "sample": (2, lambda: sample(int(args[1]), Path(args[2]), *map(int, args[3:4]))),
    }
    if not args or args[0] not in commands or len(args) - 1 < commands[args[0]][0]:
        print(__doc__)
        raise SystemExit(2)
    commands[args[0]][1]()


def _exit_unless(succeeded: bool) -> None:
    if not succeeded:
        raise SystemExit(1)
