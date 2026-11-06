"""Keeping each file a page loads small: a kind's exercises split into shards by the word they practise.

An exercise goes to shard `shard_of(its first word, count)`, a hash both the build and the page
(site/exercises.js, `shardOf`) compute alike, so a page practising one word ("Vježbaj" on its card)
loads the one shard that holds it, and a page practising a whole kind loads one shard at random.

Pure, and the same in every build.
"""

from __future__ import annotations

import json
import math
from collections.abc import Sequence

from fil.exercises.model import Exercise

MAX_SHARD_BYTES = 60_000
_FNV_OFFSET, _FNV_PRIME = 0x811C9DC5, 0x01000193


def shard_of(word: str, count: int) -> int:
    """FNV-1a (32 bits) of the word id's UTF-8 bytes, modulo the shard count."""
    hashed = _FNV_OFFSET
    for byte in word.encode("utf-8"):
        hashed = ((hashed ^ byte) * _FNV_PRIME) & 0xFFFFFFFF
    return hashed % count


def shards(exercises: Sequence[Exercise], max_bytes: int = MAX_SHARD_BYTES) -> list[list[dict]]:
    """The exercises as JSON-ready shards of about `max_bytes` each (by their first word)."""
    shown = [exercise.as_json() for exercise in exercises]
    size = sum(len(json.dumps(item, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) for item in shown)
    count = max(1, math.ceil(size / max_bytes))
    split: list[list[dict]] = [[] for _ in range(count)]
    for exercise, item in zip(exercises, shown):
        split[shard_of(exercise.words[0], count)].append(item)
    return split
