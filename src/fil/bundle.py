"""Write the read-only content.sqlite the apps load, from VerbDetail records.

The service is the single source of truth; this only shapes its output into tables
and writes them — the app reads, it never computes. Text content for now; audio
columns are added when the audio phase lands. Every conjugation cell carries its
`source` + `confidence` so the app can present attested/consensus forms as trusted
and hide or mark the rest; examples carry whether they passed the correctness gate.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from fil.service import VerbDetail


def verb_id(detail: VerbDetail) -> str:
    return f"{detail.root}_{detail.form}"


def write_bundle(details: list[VerbDetail], out_db: Path) -> dict[str, int]:
    """Write a fresh content.sqlite from the given verbs; return row counts."""
    out_db.unlink(missing_ok=True)
    out_db.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(out_db)
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        _create_schema(connection)
        counts = _insert_all(connection, details)
        connection.commit()
    finally:
        connection.close()
    return counts


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE verbs (
            verb_id TEXT PRIMARY KEY,
            root TEXT NOT NULL,
            form INTEGER NOT NULL,
            lemma TEXT NOT NULL,
            present_vowel TEXT
        );
        CREATE TABLE conjugations (
            verb_id TEXT NOT NULL REFERENCES verbs(verb_id),
            tense TEXT NOT NULL,
            pronoun TEXT NOT NULL,
            arabic TEXT NOT NULL,
            source TEXT NOT NULL,
            confidence REAL NOT NULL,
            PRIMARY KEY (verb_id, tense, pronoun)
        );
        CREATE TABLE ayat (
            verb_id TEXT NOT NULL REFERENCES verbs(verb_id),
            surah INTEGER NOT NULL,
            ayah INTEGER NOT NULL,
            PRIMARY KEY (verb_id, surah, ayah)
        );
        CREATE TABLE examples (
            example_id INTEGER PRIMARY KEY,
            verb_id TEXT NOT NULL REFERENCES verbs(verb_id),
            arabic TEXT NOT NULL,
            en TEXT NOT NULL,
            bs TEXT NOT NULL,
            tense TEXT,
            pronoun TEXT,
            passed INTEGER NOT NULL
        );
        CREATE TABLE example_words (
            example_id INTEGER NOT NULL REFERENCES examples(example_id),
            position INTEGER NOT NULL,
            arabic TEXT NOT NULL,
            en TEXT NOT NULL,
            bs TEXT NOT NULL,
            is_target INTEGER NOT NULL,
            PRIMARY KEY (example_id, position)
        );
        CREATE INDEX idx_conj_verb ON conjugations(verb_id);
        CREATE INDEX idx_ayat_verb ON ayat(verb_id);
        CREATE INDEX idx_examples_verb ON examples(verb_id);
        """
    )


def _insert_all(connection: sqlite3.Connection, details: list[VerbDetail]) -> dict[str, int]:
    counts = {"verbs": 0, "conjugations": 0, "ayat": 0, "examples": 0}
    example_id = 0
    for detail in details:
        vid = verb_id(detail)
        _insert_verb(connection, vid, detail)
        counts["verbs"] += 1
        counts["conjugations"] += _insert_conjugations(connection, vid, detail)
        counts["ayat"] += _insert_ayat(connection, vid, detail)
        for example in detail.examples:
            example_id += 1
            _insert_example(connection, example_id, vid, example)
            counts["examples"] += 1
    return counts


def _insert_verb(connection: sqlite3.Connection, vid: str, detail: VerbDetail) -> None:
    connection.execute(
        "INSERT INTO verbs VALUES (?,?,?,?,?)",
        (vid, detail.root, detail.form, detail.lemma, detail.present_vowel),
    )


def _insert_conjugations(connection: sqlite3.Connection, vid: str, detail: VerbDetail) -> int:
    rows = [(vid, c.tense, c.pronoun, c.arabic, c.source, c.confidence) for c in detail.cells]
    connection.executemany("INSERT INTO conjugations VALUES (?,?,?,?,?,?)", rows)
    return len(rows)


def _insert_ayat(connection: sqlite3.Connection, vid: str, detail: VerbDetail) -> int:
    rows = [(vid, *_split_ref(ref)) for ref in detail.ayat]
    connection.executemany("INSERT INTO ayat VALUES (?,?,?)", rows)
    return len(rows)


def _insert_example(connection: sqlite3.Connection, example_id: int, vid: str, example) -> None:
    passed = 1 if (example.checks and example.checks.passed) else 0
    connection.execute(
        "INSERT INTO examples VALUES (?,?,?,?,?,?,?,?)",
        (example_id, vid, example.arabic, example.en, example.bs,
         example.tense, example.pronoun, passed),
    )
    word_rows = [
        (example_id, position, word.arabic, word.en, word.bs, int(word.is_target))
        for position, word in enumerate(example.words)
    ]
    connection.executemany("INSERT INTO example_words VALUES (?,?,?,?,?,?)", word_rows)


def _split_ref(ref: str) -> tuple[int, int]:
    surah, ayah = ref.split(":")
    return int(surah), int(ayah)
