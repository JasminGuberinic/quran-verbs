"""Gloss the remaining Quranic forms by composition: proclitics + verb cell + object.

    fil compose status               what composition would gloss now, and why the rest are skipped
    fil compose sense-sheets DIR [N] DIR/<n>/senses.tsv: each place a polysemous verb's form stands in that has
                                     no sense chosen yet, with its ayah and the English the site shows under it — about N
    fil compose senses DIR           check every filled DIR/*/senses.tsv; merge into data/polysemous_sense_choices.json
                                     — all or nothing
    fil compose sheets DIR [PER]     DIR/<n>/cells.tsv: the Bosnian paradigm cells still to write, PER verbs a sheet
    fil compose paradigms DIR        check every filled DIR/*/cells.tsv; merge into data/bs_paradigms.json — all or nothing
    fil compose build                write data/composed_form_glosses.json (English and Bosnian), with the
                                     corrections of data/composed_gloss_corrections.json applied, and
                                     data/composed_ayah_glosses.json: the places whose gloss is not their form's
                                     (a polysemous verb's form in more than one sense; data/composed_place_corrections.json)
    fil compose sample N OUT [SEED]  a random sample of composed glosses for a blind review

Only forms without a gloss are composed: an authored gloss or an example ayah's own gloss
always wins (see fil.attested_forms.gloss_of and fil.stages.forms.read_glosses). A polysemous
verb's form is composed place by place, in the sense chosen for each ayah (fil.composition.senses).
"""

from __future__ import annotations

import json
import random
import sys
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from fil import attested_forms, meanings, service
from fil.attested_forms import AttestedForm, Location, VerbKey
from fil.ayah_translations import AyahTranslations
from fil.composition import bosnian, corrections, english, senses
from fil.composition.compose import Composed, ComposedBySense, Reading, Skipped, compose, compose_by_sense, plan
from fil.composition.decomposition import CannotCompose, Decomposition
from fil.composition.english import EnglishVerb
from fil.composition.paradigms import SHEET_COLUMNS, InvalidParadigm, from_sheet, validated, verb_key
from fil.composition.senses import InvalidSenses, PolysemousVerb
from fil.corpus.parse import iter_segments
from fil.resources import (AYAH_VERB_GLOSSES_JSON, BS_PARADIGMS_JSON, COMPOSED_AYAH_GLOSSES_JSON,
                           COMPOSED_FORM_GLOSSES_JSON, COMPOSED_GLOSS_CORRECTIONS_JSON, COMPOSED_PLACE_CORRECTIONS_JSON,
                           FORM_GLOSSES_JSON, POLYSEMOUS_SENSE_CHOICES_JSON, POLYSEMOUS_VERBS_JSON, QAC_MORPHOLOGY)
from fil.stages import forms

SHEET = "cells.tsv"
SENSE_SHEET = "senses.tsv"
SENSE_SHEET_COLUMNS = ("form", "place", "verb", "senses", "ayah", "english", "sense", "why")
VERBS_PER_SHEET = 100
PLACES_PER_SENSE_SHEET = 140
_ABOUT_GLOSSES = ("Quranic forms glossed by rule, not by hand: proclitic words + the verb's cell (English "
                  "conjugated from data/meanings.json, Bosnian from data/bs_paradigms.json) + its object. "
                  "Key: root|form|arabic. Only forms without an authored or in-context gloss; written by "
                  "`fil compose build` — regenerate rather than edit.")
_ABOUT_AYAH_GLOSSES = ("Places (surah:ayah:word) whose composed gloss is not their form's: a polysemous verb's form "
                       "standing in more than one sense (data/polysemous_sense_choices.json), or a place corrected on "
                       "its own (data/composed_place_corrections.json). Written by `fil compose build` — regenerate "
                       "rather than edit.")
_ABOUT_PARADIGMS = ("Per verb (root|form), the Bosnian of each cell the Quran uses it in: tense|voice|subject|objects "
                    "→ the cell as it opens a sentence. A polysemous verb's other sense has its own paradigm, "
                    "root|form@sense (data/polysemous_verbs.json). Filled through `fil compose sheets/paradigms`.")
_ABOUT_CHOICES = ("For each place a form of a polysemous verb (data/polysemous_verbs.json) stands in, the sense its "
                  "ayah needs and why: root|form|arabic → surah:ayah:word → {sense, why}. Chosen against the ayah "
                  "and the site's English through `fil compose sense-sheets/senses` (glosses worded after Korkut and "
                  "Sahih International); `fil compose build` refuses a choice whose form or place is gone.")

Result = Composed | ComposedBySense | Skipped


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

    @property
    def form_key(self) -> str:
        return attested_forms.form_key(self.verb, self.form.text)


# ---------------------------------------------------------------- commands

def status() -> None:
    _report(_results())


def build() -> None:
    results = _results()
    _require_fresh(read_sense_choices(), [candidate for candidate, _result in results])
    single = {candidate.form_key: gloss for candidate, result in results for gloss in (_single_gloss(result),) if gloss}
    corrected = corrections.validated(read_corrections(), {key: (gloss.en, gloss.bs) for key, gloss in single.items()})
    mixed = {candidate.form_key: result.form_gloss for candidate, result in results
             if isinstance(result, ComposedBySense) and result.is_mixed}
    glosses = {key: _gloss(corrected.get(key, gloss)) for key, gloss in single.items()} | {
        key: _gloss(gloss) for key, gloss in mixed.items()}
    at_places = dict(_place_glosses(results))
    places_corrected = corrections.validated(read_place_corrections(),
                                             {key: (gloss.en, gloss.bs) for key, (_place, gloss) in at_places.items()})
    # A mixed form's row lists every sense; each place shows its own. A corrected place shows its correction.
    ayah_glosses = {place: _gloss(gloss) for key, (place, gloss) in at_places.items() if key.split(" ")[0] in mixed}
    ayah_glosses |= {at_places[key][0]: _gloss(correction) for key, correction in places_corrected.items()}
    _write_json(COMPOSED_FORM_GLOSSES_JSON, {"_about": _ABOUT_GLOSSES, **dict(sorted(glosses.items()))})
    _write_json(COMPOSED_AYAH_GLOSSES_JSON, {"_about": _ABOUT_AYAH_GLOSSES, **dict(sorted(ayah_glosses.items()))})
    _report(results)
    print(f"  corrected in context: {len(corrected)} forms, {len(places_corrected)} places; "
          f"places glossed apart from their form: {len(ayah_glosses)}")


def _results() -> list[tuple[Candidate, Result]]:
    paradigms, verbs, choices = read_paradigms(), read_polysemous_verbs(), read_sense_choices()
    return [(candidate, _composed(candidate, paradigms, verbs, choices)) for candidate in candidates()]


def _single_gloss(result: Result) -> Composed | None:
    """The one gloss right in every ayah the form stands in, if it has one."""
    if isinstance(result, ComposedBySense) and not result.is_mixed:
        return result.form_gloss
    return result if isinstance(result, Composed) else None


def _place_glosses(results: Iterable[tuple[Candidate, Result]]) -> Iterator[tuple[str, tuple[str, Composed]]]:
    """Every place a composed form stands in, by `corrections.place_key` → (location key, the rule's gloss there)."""
    for candidate, result in results:
        if isinstance(result, Skipped):
            continue
        for location in candidate.form.locations:
            gloss = result.by_location[location] if isinstance(result, ComposedBySense) else result
            place = attested_forms.location_key(location)
            yield corrections.place_key(candidate.form_key, place), (place, gloss)


def _gloss(gloss: Composed | corrections.Correction) -> dict[str, str]:
    return {"en": gloss.en, "bs": gloss.bs}


def _require_fresh(choices: senses.Choices, found: Iterable[Candidate]) -> None:
    """A sense chosen for a form or place that is gone fails: it was judged against another text."""
    verbs = read_polysemous_verbs()
    places = {candidate.form_key: {attested_forms.location_key(location) for location in candidate.form.locations}
              for candidate in found if candidate.key in verbs}
    problems = senses.stale(choices, verbs, places)
    if problems:
        raise InvalidSenses("; ".join(problems))


def sheets(out: Path, per_sheet: int = VERBS_PER_SHEET) -> None:
    """About PER verbs a sheet, each sheet as long as the next, listing every cell a
    composable form needs and no paradigm has yet."""
    rows = _needed_rows(read_paradigms())
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
        known = read_paradigms()
        filled = [from_sheet(path.read_text(encoding="utf-8").splitlines(), known)
                  for path in sorted(folder.glob(f"*/{SHEET}"))]
    except InvalidParadigm as problem:
        print(f"compose paradigms: REFUSED, nothing written — {str(problem)[:2000]}")
        return False
    merged = {verb: dict(cells) for verb, cells in read_paradigms().items()}
    for sheet in filled:
        for verb, cells in sheet.items():
            merged.setdefault(verb, {}).update(cells)
    _write_json(BS_PARADIGMS_JSON, {"_about": _ABOUT_PARADIGMS, **validated(dict(sorted(merged.items())))})
    print(f"compose paradigms: {sum(map(len, filled))} verbs from {len(filled)} sheets → {BS_PARADIGMS_JSON.name}")
    return True


def sense_sheets(out: Path, per_sheet: int = PLACES_PER_SENSE_SHEET) -> None:
    """Every place of a composable polysemous form with no sense chosen, a verb's places kept together,
    with each sense as the form would read in it — the chooser picks a gloss, not a dictionary entry."""
    verbs, chosen = read_polysemous_verbs(), read_sense_choices()
    ayat, translations = _ayah_texts(), AyahTranslations()
    lemmas = {(verb.root, verb.form): verb.lemma for verb in service.list_verbs()}
    rows: list[tuple[str, ...]] = []
    for candidate in candidates():
        verb = verbs.get(candidate.key)
        readings = _sense_readings(candidate, verb) if verb else {}
        if not readings:
            continue
        for location in candidate.form.locations:
            place = attested_forms.location_key(location)
            if place in chosen.get(candidate.form_key, {}):
                continue
            surah, ayah, _word = location
            translated = translations.of(surah, ayah)
            rows.append((candidate.form_key, place, f"{lemmas[candidate.verb]} {candidate.meaning_en}",
                         " ; ".join(f"{sense_id} = {gloss}" for sense_id, gloss in readings.items()),
                         _marked(ayat[(surah, ayah)], location),
                         " ".join(translated.get("en", {}).get("text", "").split()),
                         "", ""))
    for number, start in enumerate(range(0, len(rows), per_sheet), 1):
        folder = out / str(number)
        folder.mkdir(parents=True, exist_ok=True)
        lines = ["\t".join(SENSE_SHEET_COLUMNS)] + ["\t".join(row) for row in _whole_verbs(rows, start, per_sheet)]
        (folder / SENSE_SHEET).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"compose sense-sheets: {len(rows)} places → {out}/<n>/{SENSE_SHEET}")


def _whole_verbs(rows: list[tuple[str, ...]], start: int, size: int) -> list[tuple[str, ...]]:
    """rows[start:start+size], except that a form's places are never split between two sheets."""
    def first_of_its_form(index: int) -> int:
        while 0 < index < len(rows) and rows[index][0] == rows[index - 1][0]:
            index += 1
        return index
    return rows[first_of_its_form(start):first_of_its_form(start + size)]


def _sense_readings(candidate: Candidate, verb: PolysemousVerb) -> dict[str, str]:
    """Each sense the form composes in → its English there ("fulfil" → "he/it fulfilled")."""
    readings = {}
    for sense in verb.senses:
        try:
            readings[sense.id] = plan(candidate.key, candidate.form, candidate.readings, sense.en).english
        except CannotCompose:
            continue
    return readings


def _marked(words: dict[int, str], location: Location) -> str:
    """The ayah, its form between « »."""
    return " ".join(f"«{text}»" if number == location[2] else text for number, text in sorted(words.items()))


def import_senses(folder: Path) -> bool:
    """Merge every filled sense sheet — all of them, or nothing."""
    try:
        filled = _read_sense_sheets(sorted(folder.glob(f"*/{SENSE_SHEET}")))
        merged = {form: dict(by_place) for form, by_place in read_sense_choices().items()}
        for form, by_place in filled.items():
            merged.setdefault(form, {}).update(by_place)
        _require_fresh(merged, candidates())
    except InvalidSenses as problem:
        print(f"compose senses: REFUSED, nothing written — {str(problem)[:2000]}")
        return False
    stored = {form: {place: {"sense": choice.sense, "why": choice.why} for place, choice in sorted(by_place.items())}
              for form, by_place in sorted(merged.items())}
    _write_json(POLYSEMOUS_SENSE_CHOICES_JSON, {"_about": _ABOUT_CHOICES, **stored})
    read_sense_choices.cache_clear()
    print(f"compose senses: {sum(map(len, filled.values()))} places → {POLYSEMOUS_SENSE_CHOICES_JSON.name}")
    return True


def _read_sense_sheets(paths: list[Path]) -> dict[str, dict[str, senses.SenseChoice]]:
    entries: dict[str, dict[str, dict[str, str]]] = {}
    for path in paths:
        rows = [line.split("\t") for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not rows or tuple(rows[0]) != SENSE_SHEET_COLUMNS:
            raise InvalidSenses(f"{path}: the sheet must open with the header {' '.join(SENSE_SHEET_COLUMNS)}")
        wrong = [str(number) for number, row in enumerate(rows[1:], 2) if len(row) != len(SENSE_SHEET_COLUMNS)]
        if wrong:
            raise InvalidSenses(f"{path} lines {', '.join(wrong[:10])}: not {len(SENSE_SHEET_COLUMNS)} columns")
        for row in rows[1:]:
            fields = dict(zip(SENSE_SHEET_COLUMNS, row))
            entries.setdefault(fields["form"], {})[fields["place"]] = {"sense": fields["sense"].strip(),
                                                                       "why": fields["why"].strip()}
    return senses.read_choices(entries)


def sample(size: int, out: Path, seed: int = 1) -> None:
    """Arabic form, its first ayah and both glosses — no code, no rule — for a blind reviewer."""
    composed = _read(COMPOSED_FORM_GLOSSES_JSON)
    by_key = {candidate.form_key: candidate for candidate in candidates(every=True)}
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


def _composed(candidate: Candidate, paradigms: dict, verbs: dict[str, PolysemousVerb], choices: senses.Choices) -> Result:
    """By rule from the verb's first sense — or, for a polysemous verb, place by place in the chosen senses."""
    verb = verbs.get(candidate.key)
    if verb is None:
        return compose(candidate.key, candidate.form, candidate.readings, candidate.meaning_en,
                       paradigms.get(candidate.key, {}))
    by_place = choices.get(candidate.form_key, {})
    chosen = {location: by_place[place].sense for location in candidate.form.locations
              for place in (attested_forms.location_key(location),) if place in by_place}
    if len(chosen) < candidate.form.count and not _sense_readings(candidate, verb):
        return _first_refusal(candidate, verb)
    return compose_by_sense(verb, candidate.form, candidate.readings, chosen, paradigms)


def _first_refusal(candidate: Candidate, verb: PolysemousVerb) -> Skipped:
    """Why a polysemous form composes in none of its senses (so no sense is ever asked for it)."""
    try:
        plan(candidate.key, candidate.form, candidate.readings, verb.senses[0].en)
    except CannotCompose as reason:
        return Skipped(reason.reason)
    return Skipped("sense not chosen")


def _needed_rows(paradigms: dict) -> list[tuple[str, ...]]:
    rows: dict[tuple[str, str], tuple[str, ...]] = {}
    lemmas = {(verb.root, verb.form): verb.lemma for verb in service.list_verbs()}
    for candidate, paradigm_key, meaning_en, meaning_bs in _to_compose(candidates()):
        try:
            planned = plan(candidate.key, candidate.form, candidate.readings, meaning_en)
        except CannotCompose:
            continue
        cell, known = planned.decomposition.cell, paradigms.get(paradigm_key, {})
        hint = english.cell_gloss(cell, EnglishVerb.from_meaning(meaning_en))
        for code, code_hint in _cells_needed(planned.decomposition, hint, known):
            if code not in known:
                rows.setdefault((paradigm_key, code), (paradigm_key, lemmas[candidate.verb], meaning_en,
                                                       meaning_bs, code, code_hint, candidate.form.text, ""))
    return list(rows.values())


def _to_compose(found: Iterable[Candidate]) -> Iterator[tuple[Candidate, str, str, str]]:
    """(candidate, paradigm key, English meaning, Bosnian meaning) for each sense a form is composed in:
    the verb's first sense, or each sense chosen for a polysemous verb's form (none while unchosen)."""
    verbs, choices = read_polysemous_verbs(), read_sense_choices()
    for candidate in found:
        verb = verbs.get(candidate.key)
        if verb is None:
            yield candidate, candidate.key, candidate.meaning_en, candidate.meaning_bs
            continue
        for sense_id in sorted({choice.sense for choice in choices.get(candidate.form_key, {}).values()}):
            sense = verb.sense(sense_id)
            yield candidate, verb.paradigm_key(sense_id), sense.en, sense.bs


def _cells_needed(decomposition: Decomposition, hint: str, known: dict[str, str]) -> list[tuple[str, str]]:
    """The form's cell, and after "da"/"neka" its perfective present too — the filler sees the
    imperfective and writes its perfective partner, or "same" where there is none."""
    cell = decomposition.cell
    needed = [(cell.code, hint)]
    if bosnian.wants_perfective(decomposition.proclitics, cell):
        imperfective = known.get(cell.code, "the present cell above")
        needed.append((bosnian.perfective_code(cell), f"{hint} — perfective of: {imperfective}"))
    return needed


def _report(results: list[tuple[Candidate, Result]]) -> None:
    reasons = Counter(result.reason for _candidate, result in results if isinstance(result, Skipped))
    composed = sum(not isinstance(result, Skipped) for _candidate, result in results)
    by_sense = sum(isinstance(result, ComposedBySense) for _candidate, result in results)
    print(f"compose: {len(results)} unglossed forms; composed {composed} ({by_sense} of polysemous verbs, "
          f"place by place); skipped {sum(reasons.values())}")
    for reason, count in reasons.most_common():
        print(f"  {count:5}  {reason}")


# ---------------------------------------------------------------- the stored data

@lru_cache(maxsize=1)
def read_polysemous() -> frozenset[str]:
    """Verbs whose first sense misleads in too many ayat: never composed from it (a table cell neither)."""
    return frozenset(_read(POLYSEMOUS_VERBS_JSON))


@lru_cache(maxsize=1)
def read_polysemous_verbs() -> dict[str, PolysemousVerb]:
    """Each polysemous verb with its senses, checked (data/polysemous_verbs.json)."""
    first_senses = {f"{meaning.root}|{meaning.form}": meaning.gloss("en") for meaning in meanings.load()}
    return senses.read_verbs(_read(POLYSEMOUS_VERBS_JSON), first_senses)


@lru_cache(maxsize=1)
def read_sense_choices() -> dict[str, dict[str, senses.SenseChoice]]:
    """The sense chosen for each place a polysemous verb's form stands in (data/polysemous_sense_choices.json)."""
    return senses.read_choices(_read(POLYSEMOUS_SENSE_CHOICES_JSON))


def read_corrections() -> dict[str, corrections.Correction]:
    """Composed glosses corrected in context (data/composed_gloss_corrections.json), checked for form only."""
    return corrections.read(_read(COMPOSED_GLOSS_CORRECTIONS_JSON))


def read_place_corrections() -> dict[str, corrections.Correction]:
    """Composed glosses corrected at one place (data/composed_place_corrections.json), by `corrections.place_key`."""
    return corrections.read_by_place(_read(COMPOSED_PLACE_CORRECTIONS_JSON))


def read_paradigms() -> dict[str, dict[str, str]]:
    return validated(_read(BS_PARADIGMS_JSON))


def _ayah_texts() -> dict[tuple[int, int], dict[int, str]]:
    """Every ayah's words as the Quran writes them, by number."""
    with QAC_MORPHOLOGY.open(encoding="utf-8") as lines:
        words = attested_forms.word_texts(iter_segments(lines))
    ayat: dict[tuple[int, int], dict[int, str]] = {}
    for (surah, ayah, word), text in words.items():
        ayat.setdefault((surah, ayah), {})[word] = text
    return ayat


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
        "sense-sheets": (1, lambda: sense_sheets(Path(args[1]), *map(int, args[2:3]))),
        "senses": (1, lambda: _exit_unless(import_senses(Path(args[1])))),
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
