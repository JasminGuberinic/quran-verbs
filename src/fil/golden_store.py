"""Read the golden set — the sentences whose verdict we already know.

A small I/O adapter, like the other stores: the comparison itself lives in `fil.evals`.
The file is committed with the code on purpose, because it is a test fixture as much as
data — it is what makes a future "simplification" of the gate fail loudly.
"""

from __future__ import annotations

import json
from pathlib import Path

from fil.evals import GoldenCase
from fil.examples import Example, ExampleWord
from fil.resources import GOLDEN_JSON


def load(path: Path = GOLDEN_JSON) -> list[GoldenCase]:
    """Every golden case, each with the verdict the gate is expected to reach."""
    return [_case(item) for item in json.loads(path.read_text(encoding="utf-8"))]


def roots(path: Path = GOLDEN_JSON) -> dict[str, str]:
    """Which root each golden sentence claims to demonstrate, keyed by its Arabic."""
    return {
        item["arabic"]: item["root"]
        for item in json.loads(path.read_text(encoding="utf-8"))
    }


def _case(item: dict) -> GoldenCase:
    return GoldenCase(
        example=Example(
            arabic=item["arabic"],
            words=tuple(ExampleWord(**word) for word in item["words"]),
            en=item["en"], bs=item["bs"],
            tense=item.get("tense"), pronoun=item.get("pronoun"),
        ),
        expect_gate_passes=item["expect_gate_passes"],
        because=item["because"],
    )
