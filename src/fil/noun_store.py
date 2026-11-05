"""The studied nouns' data files: read, validated on the way in, written back.

    data/noun_meanings.json      {"يَد|يدي": {"en", "enPlural", "bs", "countable", "idafa": {...}}}
    data/noun_tables.json        {"يَد|يدي": {"rows": [...]}}             (fil nouns batch tables)
    data/noun_bs_paradigms.json  {"يَد|يدي": {"cells", "genders", "prepositions"}}
    data/noun_sentences.json     {"يَد|يدي": [{"role": "subject", ...example}]}

A small I/O adapter; what an entry must hold is decided in fil.nouns.studied and
fil.nouns.bosnian.
"""

from __future__ import annotations

import json
from pathlib import Path

from fil.example_store import from_dict, to_dict
from fil.nouns import bosnian
from fil.nouns.bosnian import BosnianNoun
from fil.nouns.studied import (NounMeaning, NounSentence, NounTable, meaning_entry, parse_meaning, parse_table,
                               table_entry)
from fil.resources import (NOUN_BS_PARADIGMS_JSON, NOUN_MEANINGS_JSON, NOUN_OVERRIDES_JSON, NOUN_SENTENCES_JSON,
                           NOUN_TABLES_JSON)

_ABOUT = "_about"
_ABOUTS = {
    NOUN_MEANINGS_JSON.name: "The studied nouns (lemma|root): meaning in English (first sense composes the glosses) "
                             "and Bosnian, and the iḍāfa example of the card. Merged by `fil nouns batch meanings`.",
    NOUN_TABLES_JSON.name: "Each studied noun's case table: the Quran's spellings first, CAMeL's for the rest, "
                           "every form gated (fil.nouns.paradigm). Written by `fil nouns batch tables`.",
    NOUN_BS_PARADIGMS_JSON.name: "Each studied noun's Bosnian declension (number|case), the gender of each number "
                                 "(m, ma = masculine animate, f, n) and the Bosnian preposition for each Arabic one. "
                                 "Imported by `fil nouns batch paradigms`, validated by fil.nouns.bosnian.",
    NOUN_SENTENCES_JSON.name: "Practice sentences per noun and role (subject, object, preposition, possession), "
                              "gated by fil.nouns.sentence_gate and read by a blind reviewer.",
}


def load_meanings(path: Path = NOUN_MEANINGS_JSON) -> list[NounMeaning]:
    return [parse_meaning(key, entry) for key, entry in _entries(path).items()]


def save_meanings(meanings: list[NounMeaning], path: Path = NOUN_MEANINGS_JSON) -> None:
    _write(path, {meaning.key: meaning_entry(meaning) for meaning in meanings})


def load_tables(path: Path = NOUN_TABLES_JSON) -> dict[str, NounTable]:
    return {key: parse_table(key, entry) for key, entry in _entries(path).items()}


def save_tables(tables: dict[str, NounTable], path: Path = NOUN_TABLES_JSON) -> None:
    _write(path, {key: table_entry(table) for key, table in tables.items()})


def load_overrides(path: Path = NOUN_OVERRIDES_JSON) -> dict[str, dict[str, dict[str, str]]]:
    """Documented cell spellings (fil.nouns.table.with_documented); each must say why."""
    entries = _entries(path)
    undocumented = [f"{key} {code}" for key, cells in entries.items() for code, entry in cells.items()
                    if not entry.get("text") or not entry.get("why")]
    if undocumented:
        raise ValueError(f"noun overrides need a text and a why: {', '.join(undocumented)}")
    return entries


def load_bosnian(needs: dict[str, tuple[str, ...]] | None = None,
                 path: Path = NOUN_BS_PARADIGMS_JSON) -> dict[str, BosnianNoun]:
    """The stored declensions, validated; `needs` (key → numbers) also demands their cells."""
    return bosnian.validated(_entries(path), needs or {})


def save_bosnian_entries(entries: dict[str, dict], path: Path = NOUN_BS_PARADIGMS_JSON) -> None:
    _write(path, entries)


def bosnian_entries(path: Path = NOUN_BS_PARADIGMS_JSON) -> dict[str, dict]:
    return _entries(path)


def load_sentences(path: Path = NOUN_SENTENCES_JSON) -> list[NounSentence]:
    return [NounSentence(key, item["role"], from_dict(item["example"]))
            for key, items in _entries(path).items() for item in items]


def save_sentences(sentences: list[NounSentence], path: Path = NOUN_SENTENCES_JSON) -> None:
    grouped: dict[str, list[dict]] = {}
    for sentence in sentences:
        grouped.setdefault(sentence.key, []).append({"role": sentence.role, "example": to_dict(sentence.example)})
    _write(path, grouped)


def _entries(path: Path) -> dict:
    if not path.exists():
        return {}
    return {key: value for key, value in json.loads(path.read_text(encoding="utf-8")).items() if key != _ABOUT}


def _write(path: Path, entries: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {_ABOUT: _ABOUTS.get(path.name, ""), **entries}
    path.write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
