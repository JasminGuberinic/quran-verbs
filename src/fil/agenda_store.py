"""Persist the agenda, so what the factory owes survives the session that planned it.

A small I/O adapter over `data/agenda.json`, mirroring `example_store`: the pure state
machine lives in `fil.agenda`, and this only reads and writes it. Jobs are keyed so a
save is a merge by identity rather than an append — recording the same job twice updates
it instead of duplicating it.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from fil.agenda import Job
from fil.resources import AGENDA_JSON


def load(path: Path = AGENDA_JSON) -> list[Job]:
    """Every job the factory knows about (empty if the agenda has never been written)."""
    return [Job(**item) for item in _read(path)]


def save(jobs: list[Job], path: Path = AGENDA_JSON) -> None:
    """Replace the agenda with these jobs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(job) for job in jobs]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def upsert(updated: list[Job], path: Path = AGENDA_JSON) -> list[Job]:
    """Merge these jobs into the agenda by identity, and return the whole agenda.

    Merging by key is what keeps the agenda idempotent: re-planning a verb or re-recording
    an outcome overwrites that one job and leaves every other untouched.
    """
    agenda = {job.key: job for job in load(path)}
    agenda.update({job.key: job for job in updated})
    merged = list(agenda.values())
    save(merged, path)
    return merged


def find(key: str, path: Path = AGENDA_JSON) -> Job | None:
    """One job by its key, or None if the agenda has no such cell."""
    return next((job for job in load(path) if job.key == key), None)


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))
