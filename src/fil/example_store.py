"""Persist practice examples, keyed by verb, in a single JSON file.

This is a small I/O adapter over `data/examples.json`. Examples are authored/generated
content that must survive across runs and ship in the bundle, so they live in the repo
(unlike the derived build/ artefacts).
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from fil.examples import Critique, Example, ExampleChecks, ExampleWord
from fil.resources import EXAMPLES_JSON


def load(root: str, form: int, path: Path = EXAMPLES_JSON) -> list[Example]:
    """The stored examples for one verb (empty list if none)."""
    return [_from_dict(item) for item in _read(path).get(_key(root, form), [])]


def save(root: str, form: int, examples: list[Example], path: Path = EXAMPLES_JSON) -> None:
    """Replace the stored examples for one verb."""
    store = _read(path)
    store[_key(root, form)] = [asdict(example) for example in examples]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")


def stored_verbs(path: Path = EXAMPLES_JSON) -> list[tuple[str, int]]:
    """Every (root, form) that has stored examples."""
    verbs = []
    for key in _read(path):
        root, form = key.rsplit("_", 1)
        verbs.append((root, int(form)))
    return verbs


def _key(root: str, form: int) -> str:
    return f"{root}_{form}"


def _read(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _from_dict(data: dict) -> Example:
    return Example(
        arabic=data["arabic"],
        words=tuple(ExampleWord(**word) for word in data["words"]),
        en=data["en"],
        bs=data["bs"],
        tense=data.get("tense"),
        pronoun=data.get("pronoun"),
        source=data.get("source", "generated"),
        drafted_by=data.get("drafted_by", ""),  # who wrote it must survive a reload, or the
        checks=_checks_from(data.get("checks")),  # self-review check has nothing to compare
        critique=Critique(**data["critique"]) if data.get("critique") else None,
    )


def _checks_from(data: dict | None) -> ExampleChecks | None:
    """Rebuild the checks, tolerating files written before a check existed."""
    if not data:
        return None
    conflicts = tuple(data.get("gloss_conflicts", ()))  # JSON has no tuples
    return ExampleChecks(**{**data, "gloss_conflicts": conflicts})
