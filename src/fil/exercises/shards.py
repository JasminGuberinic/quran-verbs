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
_SLACK = 1.25   # how far over its budget a shard may go before the kind is split further
_FNV_OFFSET, _FNV_PRIME = 0x811C9DC5, 0x01000193


def shard_of(word: str, count: int) -> int:
    """FNV-1a (32 bits) of the word id's UTF-8 bytes, modulo the shard count."""
    hashed = _FNV_OFFSET
    for byte in word.encode("utf-8"):
        hashed = ((hashed ^ byte) * _FNV_PRIME) & 0xFFFFFFFF
    return hashed % count


def shards(exercises: Sequence[Exercise], max_bytes: int = MAX_SHARD_BYTES) -> list[list[dict]]:
    """The exercises as JSON-ready shards of about `max_bytes` each (by their first word).

    The fewest shards the size asks for, and more while a shard is far over its budget — words hash
    unevenly, and a word with many questions (قَالَ in the Quran) must not share its file with another
    such word. Never more shards than words: a word's questions are never split."""
    shown = [exercise.as_json() for exercise in exercises]
    sizes = [len(json.dumps(item, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) for item in shown]
    words = [exercise.words[0] for exercise in exercises]
    count = max(1, math.ceil(sum(sizes) / max_bytes))
    while count < len(set(words)) and max(_shard_sizes(words, sizes, count)) > max_bytes * _SLACK:
        count += 1
    split: list[list[dict]] = [[] for _ in range(count)]
    for word, item in zip(words, shown):
        split[shard_of(word, count)].append(item)
    return split


def _shard_sizes(words: Sequence[str], sizes: Sequence[int], count: int) -> list[int]:
    totals = [0] * count
    for word, size in zip(words, sizes):
        totals[shard_of(word, count)] += size
    return totals
