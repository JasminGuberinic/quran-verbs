"""The studied adjectives' data files: read, validated on the way in, written back.

    data/adjective_meanings.json         {"كَبِير|كبر": {"en", "bs", "bsShort", "bsLong", "feminine", "nouns", ...}}
    data/adjective_tables.json           {"كَبِير|كبر": {"masculine": {"rows": [...]}, "feminine": {"rows": [...]}}}
    data/adjective_overrides.json        {"قَرِيب|قرب": {"F": {"S|definite|NOM": {"text", "why"}}}}
    data/adjective_sentences.json        {"كَبِير|كبر": [{"role": "masculine", ...example}]}
    data/adjective_example_reviews.json  {"<Arabic of an agreement example>": {"approved", "note", "by"}}

A small I/O adapter; what an entry must hold is decided in fil.adjectives.model.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from fil.adjectives.model import AdjectiveMeaning, AdjectiveTable, meaning_entry, parse_meaning
from fil.example_store import from_dict, to_dict
from fil.examples import Example
from fil.nouns.studied import parse_table, table_entry
from fil.resources import (ADJECTIVE_EXAMPLE_REVIEWS_JSON, ADJECTIVE_MEANINGS_JSON, ADJECTIVE_OVERRIDES_JSON,
                           ADJECTIVE_SENTENCES_JSON, ADJECTIVE_TABLES_JSON)

_ABOUT = "_about"
_ABOUTS = {
    ADJECTIVE_MEANINGS_JSON.name: "The studied adjectives (lemma|root): meaning in English and Bosnian (bsShort/bsLong: "
                                  "the short and long masculine nominative), the feminine, the pattern, the category, the "
                                  "nouns the agreement examples use. Merged by `fil adjectives batch meanings`.",
    ADJECTIVE_TABLES_JSON.name: "Each studied adjective's masculine and feminine case tables: the Quran's spellings "
                                "first, CAMeL's (one gender asked at a time) or a documented broken plural for the rest, "
                                "every form gated (fil.adjectives.table). Written by `fil adjectives batch tables`.",
    ADJECTIVE_SENTENCES_JSON.name: "Practice sentences per adjective and role (masculine, feminine, predicate, plural), "
                                   "gated for agreement by fil.adjectives.sentence_gate and read by a blind reviewer.",
    ADJECTIVE_EXAMPLE_REVIEWS_JSON.name: "A blind reader's verdict on each agreement example a card shows "
                                         "(fil.adjectives.explanation); only approved examples ship.",
}


@dataclass(frozen=True)
class AdjectiveSentence:
    key: str
    role: str
    example: Example


@dataclass(frozen=True)
class ExampleReview:
    approved: bool
    note: str
    by: str


def load_meanings(path: Path = ADJECTIVE_MEANINGS_JSON) -> list[AdjectiveMeaning]:
    return [parse_meaning(key, entry) for key, entry in _entries(path).items()]


def save_meanings(meanings: list[AdjectiveMeaning], path: Path = ADJECTIVE_MEANINGS_JSON) -> None:
    _write(path, {meaning.key: meaning_entry(meaning) for meaning in meanings})


def load_tables(path: Path = ADJECTIVE_TABLES_JSON) -> dict[str, AdjectiveTable]:
    return {key: AdjectiveTable(key, parse_table(key, entry["masculine"]), parse_table(key, entry["feminine"]),
                                entry.get("elative"))
            for key, entry in _entries(path).items()}


def save_tables(tables: dict[str, AdjectiveTable], path: Path = ADJECTIVE_TABLES_JSON) -> None:
    _write(path, {key: {"masculine": table_entry(table.masculine), "feminine": table_entry(table.feminine),
                        **({"elative": table.elative} if table.elative else {})}
                  for key, table in tables.items()})


def load_overrides(path: Path = ADJECTIVE_OVERRIDES_JSON) -> dict[str, dict[str, dict[str, dict[str, str]]]]:
    """Documented cell spellings per gender (fil.nouns.table.with_documented); each must say why."""
    entries = _entries(path)
    undocumented = [f"{key} {gender} {code}" for key, sides in entries.items() for gender, cells in sides.items()
                    for code, entry in cells.items() if not entry.get("text") or not entry.get("why")]
    if undocumented:
        raise ValueError(f"adjective overrides need a text and a why: {', '.join(undocumented)}")
    return entries


def load_sentences(path: Path = ADJECTIVE_SENTENCES_JSON) -> list[AdjectiveSentence]:
    return [AdjectiveSentence(key, item["role"], from_dict(item["example"]))
            for key, items in _entries(path).items() for item in items]


def save_sentences(sentences: list[AdjectiveSentence], path: Path = ADJECTIVE_SENTENCES_JSON) -> None:
    grouped: dict[str, list[dict]] = {}
    for sentence in sentences:
        grouped.setdefault(sentence.key, []).append({"role": sentence.role, "example": to_dict(sentence.example)})
    _write(path, grouped)


def load_example_reviews(path: Path = ADJECTIVE_EXAMPLE_REVIEWS_JSON) -> dict[str, ExampleReview]:
    entries = _entries(path)
    unexplained = [text for text, entry in entries.items() if not entry["approved"] and not entry.get("note")]
    if unexplained:
        raise ValueError(f"{path.name}: a refused example must say why: {unexplained[:3]}")
    return {text: ExampleReview(entry["approved"], entry.get("note", ""), entry["by"]) for text, entry in entries.items()}


def save_example_reviews(reviews: dict[str, ExampleReview], path: Path = ADJECTIVE_EXAMPLE_REVIEWS_JSON) -> None:
    _write(path, {text: {"approved": review.approved, "note": review.note, "by": review.by}
                  for text, review in reviews.items()})


def _entries(path: Path) -> dict:
    if not path.exists():
        return {}
    return {key: value for key, value in json.loads(path.read_text(encoding="utf-8")).items() if key != _ABOUT}


def _write(path: Path, entries: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {_ABOUT: _ABOUTS.get(path.name, ""), **entries}
    path.write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
