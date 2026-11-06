"""Ayah quotations inside our own texts: only words we are free to publish.

The nuance groups, particles and pronouns explain an ayah by quoting it. A modern translation
under copyright must never be what we quote — not word for word, not closely paraphrased. So
the texts keep one convention, and this gate holds them to it:

  - **double quotation marks quote an ayah** (en “…”, bs „…“). Everything else in quotation
    marks — a gloss, a meaning, a term — takes single ones (en ‘…’, bs ‚…‘ or ‘…’);
  - every quotation names its ayah: the ayah the text is written for (an item's `ref`), or a
    reference written in the same text (“…”, 52:21);
  - **English** quotes only the shipped translation (Pickthall, public domain): each part of the
    quotation — parts are split at an ellipsis and at a reference inside the quotation,
    “… (107:5) …” — is found word for word in one of the named ayat, letter case, punctuation and
    anything in brackets aside (square brackets are for our own insertions);
  - **Bosnian** has no translation we may ship, so a Bosnian quotation is our own translation from
    the Arabic, and the entry says so: `"ayahQuotes": {"bs": "own"}`. Sahih International and
    Korkut remain references for single terms only.

Pure: the texts come in as the data files' entries, the English as {(surah, ayah): text}.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass

Reference = tuple[int, int]

OWN_TRANSLATION = "own"
DECLARATION = "ayahQuotes"
LANGUAGES = ("bs", "en")
_REVIEWER_ONLY = frozenset({"notes", "sources", "verified", DECLARATION})
_DOUBLE_QUOTED = {
    "en": re.compile(r'“([^”]*)”|"([^"]*)"'),
    "bs": re.compile(r'„([^“”]*)[“”]|“([^”]*)”|"([^"]*)"'),
}
_REFERENCE = re.compile(r"\b(\d{1,3}):(\d{1,3})(?::\d{1,3})?(?:\s*[–-]\s*(\d{1,3})\b(?!:))?")
_PART_BREAK = re.compile(r"…|\.\.\.|\(\s*\d{1,3}:\d{1,3}(?:\s*[–-]\s*\d{1,3})?\s*\)")
_BRACKETED = re.compile(r"\([^()]*\)|\[[^\[\]]*\]")
_WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


@dataclass(frozen=True)
class Quotation:
    """A double-quoted passage of one text, and the ayat its text speaks of."""

    where: str
    language: str
    words: str
    ayat: tuple[Reference, ...]


def problems(entries: Mapping[str, Mapping], english: Mapping[Reference, str]) -> list[str]:
    """Every quotation that breaks the convention; empty when the texts may ship."""
    found: list[str] = []
    for key, entry in entries.items():
        if key.startswith("_"):
            continue
        quotations = list(quotations_of(key, entry))
        found += _undeclared_bosnian(key, entry, quotations)
        found += [problem for quotation in quotations for problem in _quotation_problems(quotation, english)]
    return found


def quotations_of(key: str, entry: Mapping) -> Iterator[Quotation]:
    """Every double-quoted passage of the entry's learner-facing texts, in both languages."""
    for where, language, text, ayat in _texts(entry, key, ()):
        named = (*ayat, *references_in(text))
        for match in _DOUBLE_QUOTED[language].finditer(text):
            words = next(group for group in match.groups() if group is not None)
            yield Quotation(where=where, language=language, words=words, ayat=tuple(dict.fromkeys(named)))


def references_in(text: str) -> tuple[Reference, ...]:
    """The ayat a text names: 52:21, 70:18:2 (a word of it), 2:5–7 (a run)."""
    found: list[Reference] = []
    for match in _REFERENCE.finditer(text):
        surah, first = int(match.group(1)), int(match.group(2))
        last = int(match.group(3)) if match.group(3) else first
        found += [(surah, ayah) for ayah in range(first, max(first, last) + 1)]
    return tuple(found)


def is_quoted_from(words: str, ayat_texts: list[str]) -> bool:
    """Each part of the quotation stands word for word in one of the texts."""
    texts = [f" {_normalised(text)} " for text in ayat_texts]
    parts = [_normalised(part) for part in _PART_BREAK.split(words)]
    return all(any(f" {part} " in text for text in texts) for part in parts if part)


def _normalised(text: str) -> str:
    """Lower case, brackets and their contents gone, punctuation gone: the words alone."""
    while _BRACKETED.search(text):
        text = _BRACKETED.sub(" ", text)
    return " ".join(_WORD.findall(text.lower().replace("’", "'")))


def _texts(node, where: str, ayat: tuple[Reference, ...]) -> Iterator[tuple[str, str, str, tuple[Reference, ...]]]:
    """(where, language, text, the ayah it is written for) for every bs/en text under the node."""
    if isinstance(node, Mapping):
        ayat = (*ayat, *references_in(node["ref"])) if isinstance(node.get("ref"), str) else ayat
        for field, value in node.items():
            if field in _REVIEWER_ONLY:
                continue
            if field in LANGUAGES and isinstance(value, str):
                yield f"{where}/{field}", field, value, ayat
                continue
            yield from _texts(value, f"{where}/{field}", ayat)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            yield from _texts(item, f"{where}/{index}", ayat)


def _quotation_problems(quotation: Quotation, english: Mapping[Reference, str]) -> list[str]:
    shown = f"{quotation.where}: {_marks(quotation)}"
    if not quotation.ayat:
        return [f"{shown} — double quotation marks quote an ayah: name it (s:a) in the text, "
                f"or put a gloss in single quotation marks"]
    if quotation.language != "en":
        return []
    missing = [f"{surah}:{ayah}" for surah, ayah in quotation.ayat if (surah, ayah) not in english]
    if missing:
        return [f"{shown} — no English translation of {', '.join(missing)}"]
    if is_quoted_from(quotation.words, [english[reference] for reference in quotation.ayat]):
        return []
    named = ", ".join(f"{surah}:{ayah}" for surah, ayah in quotation.ayat)
    return [f"{shown} — not the shipped English (Pickthall) of {named}: quote it exactly, "
            f"or paraphrase without quotation marks"]


def _undeclared_bosnian(key: str, entry: Mapping, quotations: list[Quotation]) -> list[str]:
    if not any(quotation.language == "bs" for quotation in quotations):
        return []
    declared = entry.get(DECLARATION)
    if isinstance(declared, Mapping) and declared.get("bs") == OWN_TRANSLATION:
        return []
    return [f'{key}: quotes ayat in Bosnian but does not declare them our own translation from the Arabic '
            f'(`"{DECLARATION}": {{"bs": "{OWN_TRANSLATION}"}}`; never Korkut\'s or another\'s wording)']


def _marks(quotation: Quotation) -> str:
    opening, closing = ("„", "“") if quotation.language == "bs" else ("“", "”")
    return f"{opening}{quotation.words}{closing}"
