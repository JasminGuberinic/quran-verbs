"""Where a card's sound goes: the strategy behind every play button.

A card names each clip by a reference the page can hand to `new Audio(...)`. Two ways to
make one, never mixed in one build:

  - EmbeddedAudio: the clip itself, as a data URI — the self-contained study site
    (`fil site`), one file per verb, nothing else to carry;
  - PublishedAudio: a separate file named by its content (audio/<hash>.m4a) — the public
    site (`fil pages`), where the same clip used by ten verbs is stored and downloaded once,
    so hundreds of verbs stay well inside free hosting limits.
"""

from __future__ import annotations

import base64
import hashlib
import shutil
from pathlib import Path
from typing import Protocol

AUDIO_FOLDER = "audio"
_HASH_LENGTH = 20   # hex digits of SHA-256: far beyond any collision among our clips


class AudioSink(Protocol):
    def reference(self, clip: Path) -> str:
        """What a card stores to play `clip`."""


class EmbeddedAudio:
    def reference(self, clip: Path) -> str:
        return "data:audio/mp4;base64," + base64.b64encode(clip.read_bytes()).decode()


def published_name(content: bytes) -> str:
    """The clip's address: the same sound always gets the same name, a different one never does."""
    return f"{AUDIO_FOLDER}/{hashlib.sha256(content).hexdigest()[:_HASH_LENGTH]}.m4a"


class PublishedAudio:
    """Copies each distinct clip once into `site`/audio and refers to it relative to the site root."""

    def __init__(self, site: Path) -> None:
        self._site = site
        self._names: dict[Path, str] = {}

    def reference(self, clip: Path) -> str:
        if clip not in self._names:
            self._names[clip] = self._publish(clip)
        return self._names[clip]

    def _publish(self, clip: Path) -> str:
        name = published_name(clip.read_bytes())
        target = self._site / name
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(clip, target)
        return name
