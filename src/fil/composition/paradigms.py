"""Bosnian paradigms: per verb, the Bosnian of each cell the Quran uses it in.

Stored in data/bs_paradigms.json as {"root|form": {"past|act|3MP|-": "rekli su", …}}.
Written once per verb (by a model, from a sheet listing exactly the cells needed) and
checked here on the way in: a blank cell, a stray tab or a word in another script would
otherwise reach a learner as a gloss.

A perfective cell (the present after "da"/"neka", see fil.composition.bosnian) may be filled
with "same" when the verb's perfective present is its present ("da vjeruju"); it is resolved
to that present cell on import, so the stored paradigm only ever holds Bosnian.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

from fil.composition.bosnian import PERFECTIVE, starts_with_enclitic
from fil.composition.decomposition import TENSES

Paradigms = Mapping[str, Mapping[str, str]]   # verb key → cell code → Bosnian

# Bosnian in Latin script: letters (with čćžšđ), spaces, an apostrophe or hyphen, a closing "!".
_BOSNIAN = re.compile(r"^[a-zA-ZčćžšđČĆŽŠĐ' -]+!?$")
_CELL = re.compile(r"^(%s)\|(act|pass)\|(1S|1P|2MS|2FS|2MP|2FP|2D|3MS|3FS|3MP|3FP|3MD|3FD|3D)\|(-|[0-9A-Z+]+)$"
                   % "|".join((*TENSES, PERFECTIVE)))
SAME = "same"   # a perfective cell that is the present cell word for word
SHEET_COLUMNS = ("verb", "lemma", "meaning_en", "meaning_bs", "cell", "english", "example", "bs")


class InvalidParadigm(ValueError):
    """A paradigm cell that must not become a gloss; the message names every problem."""


def verb_key(root: str, form: int) -> str:
    return f"{root}|{form}"


def validated(paradigms: Paradigms) -> dict[str, dict[str, str]]:
    """The paradigms as plain dicts, or InvalidParadigm listing every bad cell."""
    problems = [problem for verb, cells in paradigms.items() for code, text in cells.items()
                for problem in _problems(verb, code, text)]
    if problems:
        raise InvalidParadigm("; ".join(problems))
    return {verb: dict(cells) for verb, cells in paradigms.items()}


def from_sheet(lines: Iterable[str], known: Paradigms | None = None) -> dict[str, dict[str, str]]:
    """A filled sheet (tab-separated, SHEET_COLUMNS, header first) → validated paradigms;
    a perfective "same" becomes the present cell, from the sheet itself or from `known`."""
    rows = [line.rstrip("\n").split("\t") for line in lines if line.strip()]
    if not rows or tuple(rows[0]) != SHEET_COLUMNS:
        raise InvalidParadigm(f"the sheet must open with the header {' '.join(SHEET_COLUMNS)}")
    wrong_width = [str(number) for number, row in enumerate(rows[1:], 2) if len(row) != len(SHEET_COLUMNS)]
    if wrong_width:
        raise InvalidParadigm(f"lines {', '.join(wrong_width[:10])}: not {len(SHEET_COLUMNS)} columns")
    paradigms: dict[str, dict[str, str]] = {}
    for row in rows[1:]:
        fields = dict(zip(SHEET_COLUMNS, row))
        paradigms.setdefault(fields["verb"], {})[fields["cell"]] = fields["bs"].strip()
    return validated(_with_same_resolved(paradigms, known or {}))


def _with_same_resolved(paradigms: Paradigms, known: Paradigms) -> dict[str, dict[str, str]]:
    """Every perfective "same" replaced by its present cell; one with no present stays to be refused."""
    def resolved(verb: str, code: str, text: str) -> str:
        if text != SAME or not code.startswith(f"{PERFECTIVE}|"):
            return text
        present = "present" + code[len(PERFECTIVE):]
        return paradigms[verb].get(present) or known.get(verb, {}).get(present) or text
    return {verb: {code: resolved(verb, code, text) for code, text in cells.items()}
            for verb, cells in paradigms.items()}


def _problems(verb: str, code: str, text: str) -> list[str]:
    where = f"{verb} {code}"
    if not _CELL.match(code):
        return [f"{where}: no such cell"]
    if not text.strip():
        return [f"{where}: empty"]
    if not _BOSNIAN.match(text) or "  " in text:
        return [f"{where}: not plain Bosnian in Latin script: {text!r}"]
    if text == SAME:
        return [f"{where}: \"same\" only stands for a perfective whose present cell is known"]
    if starts_with_enclitic(text):
        return [f"{where}: opens with an enclitic: {text!r}"]
    return []
