"""Package the built dataset + audio into the read-only SQLite the app loads.

Building the database is also an INTEGRITY GATE: every conjugated form must have
a matching audio clip, and each clip's SHA-256 is stored so the app (or CI) can
verify nothing drifted between the database and the shipped audio. A form without
audio fails the build — it must never reach a learner.

Design: the row-shaping logic is pure (a `sha256_of` function is injected), so it
is unit-testable with a fake hasher; the real hasher reads files and fails fast on
a missing clip; the SQLite writing is the only side effect.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from fil.audio import clip_key

# A function that, given an audio file name, returns its SHA-256 (or raises).
Sha256Of = Callable[[str], str]


@dataclass(frozen=True)
class VerbRow:
    """One row of the `verbs` table."""

    verb_id: str
    root: str
    form_number: int
    dictionary_form: str  # the vocalized past-3ms form
    ayat: str             # comma-joined "surah:ayah" refs (empty until QAC join)


@dataclass(frozen=True)
class GlossRow:
    """One meaning of one verb in one UI language (`verb_glosses` table)."""

    verb_id: str
    lang: str   # "en", "bs", …
    text: str


@dataclass(frozen=True)
class ConjugationRow:
    """One row of the `conjugations` table — one form of one verb."""

    verb_id: str
    tense: str
    pronoun: str
    arabic: str           # the vocalized form
    audio_file: str       # "<key>.m4a"
    audio_sha256: str


# ── Pure shaping (no I/O beyond the injected hasher) ──────────────────────────

def verb_row(record: dict) -> VerbRow:
    """Map a dataset record onto a `verbs` row."""
    return VerbRow(
        verb_id=record["id"],
        root=record["root"],
        form_number=record["form"],
        dictionary_form=record["past3ms"],
        ayat=",".join(record.get("ayat") or ()),
    )


def gloss_rows(record: dict) -> list[GlossRow]:
    """Map a verb's per-language meanings onto `verb_glosses` rows."""
    return [
        GlossRow(verb_id=record["id"], lang=lang, text=text)
        for lang, text in record["glosses"].items()
    ]


def conjugation_rows(record: dict, sha256_of: Sha256Of) -> list[ConjugationRow]:
    """Map every conjugation cell of a verb onto a `conjugations` row.

    The audio file name is derived from the same structural key the audio factory
    used, so the database and the clips are bound by construction, not by chance.
    """
    rows: list[ConjugationRow] = []
    for tense, cells in record["conjugation"].items():
        for pronoun, arabic in cells.items():
            audio_file = f"{clip_key(record['id'], tense, pronoun)}.m4a"
            rows.append(
                ConjugationRow(
                    verb_id=record["id"],
                    tense=tense,
                    pronoun=pronoun,
                    arabic=arabic,
                    audio_file=audio_file,
                    audio_sha256=sha256_of(audio_file),
                )
            )
    return rows


# ── Side effects: hashing files and writing the database ──────────────────────

def sha256_reader(audio_dir: Path) -> Sha256Of:
    """Build a hasher that reads a clip from `audio_dir`, failing if it's absent."""

    def read(audio_file: str) -> str:
        path = audio_dir / audio_file
        if not path.exists():
            raise FileNotFoundError(f"missing audio clip for form: {audio_file}")
        return hashlib.sha256(path.read_bytes()).hexdigest()

    return read


def write_database(
    verbs: list[VerbRow],
    glosses: list[GlossRow],
    conjugations: list[ConjugationRow],
    out_db: Path,
) -> None:
    """Write a fresh read-only-friendly SQLite with indexes."""
    out_db.unlink(missing_ok=True)
    out_db.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(out_db)
    try:
        connection.execute("PRAGMA foreign_keys=ON")  # enforce the FK integrity
        _create_schema(connection)
        _insert_verbs(connection, verbs)
        _insert_glosses(connection, glosses)
        _insert_conjugations(connection, conjugations)
        connection.commit()
    finally:
        connection.close()


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE verbs (
            verb_id TEXT PRIMARY KEY,
            root TEXT NOT NULL,
            form_number INTEGER NOT NULL,
            dictionary_form TEXT NOT NULL,
            ayat TEXT NOT NULL
        );
        CREATE TABLE verb_glosses (
            verb_id TEXT NOT NULL REFERENCES verbs(verb_id),
            lang TEXT NOT NULL,
            text TEXT NOT NULL,
            PRIMARY KEY (verb_id, lang)
        );
        CREATE TABLE conjugations (
            verb_id TEXT NOT NULL REFERENCES verbs(verb_id),
            tense TEXT NOT NULL,
            pronoun TEXT NOT NULL,
            arabic TEXT NOT NULL,
            audio_file TEXT NOT NULL,
            audio_sha256 TEXT NOT NULL,
            PRIMARY KEY (verb_id, tense, pronoun)
        );
        CREATE INDEX idx_conj_verb ON conjugations(verb_id);
        """
    )


def _insert_verbs(connection: sqlite3.Connection, verbs: list[VerbRow]) -> None:
    connection.executemany(
        "INSERT INTO verbs VALUES (:verb_id,:root,:form_number,:dictionary_form,:ayat)",
        [v.__dict__ for v in verbs],
    )


def _insert_glosses(connection: sqlite3.Connection, glosses: list[GlossRow]) -> None:
    connection.executemany(
        "INSERT INTO verb_glosses VALUES (:verb_id,:lang,:text)",
        [g.__dict__ for g in glosses],
    )


def _insert_conjugations(
    connection: sqlite3.Connection, conjugations: list[ConjugationRow]
) -> None:
    connection.executemany(
        "INSERT INTO conjugations VALUES (:verb_id,:tense,:pronoun,:arabic,:audio_file,:audio_sha256)",
        [c.__dict__ for c in conjugations],
    )


def package(
    records: list[dict], audio_dir: Path, out_db: Path, qa_passed_keys: set[str]
) -> tuple[int, int]:
    """Build the SQLite from records + audio; return (verb_count, form_count).

    Refuses to package any form whose audio has not passed the QA gate, so a
    silent/clipped clip cannot slip through between the audio and packaging
    stages. This is the integrity gate CLAUDE.md requires.
    """
    _require_qa_passed(records, qa_passed_keys)
    hasher = sha256_reader(audio_dir)
    verbs = [verb_row(record) for record in records]
    glosses = [row for record in records for row in gloss_rows(record)]
    conjugations = [row for record in records for row in conjugation_rows(record, hasher)]
    write_database(verbs, glosses, conjugations, out_db)
    return len(verbs), len(conjugations)


def _require_qa_passed(records: list[dict], qa_passed_keys: set[str]) -> None:
    """Fail fast if any form's audio is not in the set of QA-passed clips."""
    for record in records:
        for tense, cells in record["conjugation"].items():
            for pronoun in cells:
                key = clip_key(record["id"], tense, pronoun)
                if key not in qa_passed_keys:
                    raise RuntimeError(
                        f"form '{key}' has not passed audio QA — refusing to package"
                    )
