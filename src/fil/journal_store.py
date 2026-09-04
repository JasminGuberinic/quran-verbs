"""Append the journal to disk, one JSON object per line, and never rewrite a line.

JSONL rather than a JSON array on purpose: appending is a single write with no read-modify-
write cycle, so two sessions recording at once cannot lose each other's events the way they
could with a file that has to be parsed and re-serialised. The format also survives a
truncated write — one broken last line, not a corrupt file.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from fil.journal import Event
from fil.resources import JOURNAL_JSONL


def append(event: Event, path: Path = JOURNAL_JSONL) -> Event:
    """Write one event. The only write this module offers — nothing here edits or deletes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as lines:
        lines.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
    return event


def read(path: Path = JOURNAL_JSONL) -> list[Event]:
    """Every event ever recorded, in order (empty if nothing has happened yet).

    A trailing partial line — a write cut short — is skipped rather than raised, because a
    torn last line must not make the whole history unreadable.
    """
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            events.append(Event(**json.loads(line)))
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
    return events
