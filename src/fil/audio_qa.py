"""Audio QA gate: catch wrong/missing/glitchy clips before they ship.

The decision logic (`evaluate`) is a pure function of measured stats, so it is
unit-testable without touching a decoder. Two ways to measure a clip:

  - `measure`: ffmpeg/ffprobe, for the legacy per-form clips (fil audio);
  - `decoded_stats`: afconvert decodes the clip to float PCM (fil.audio) and
    `wave_stats` reads it (fil.pcm) — the site's clips (fil.clip_gate), no ffmpeg needed.

For a religious app this gate is non-negotiable: a silent, truncated, or clipped
clip must fail the build, not reach a learner.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from fil.audio import DecodeFailed, decoded_wave
from fil.pcm import FULL_SCALE_DB, NotFloatWave, read_float_wave

# Peak below this is effectively silence (a failed/empty render).
_SILENCE_CEILING_DB = -50.0


@dataclass(frozen=True)
class ClipStats:
    """What we measure about one produced clip."""

    key: str
    duration_s: float
    max_volume_db: float


@dataclass(frozen=True)
class DurationBounds:
    """How long a clip of one kind may be; outside them it is truncated or a runaway render."""

    shortest_s: float
    longest_s: float


# A single spoken verb form (fil audio).
FORM_DURATION = DurationBounds(shortest_s=0.2, longest_s=3.0)
# Any clip the site ships: a recited word can be a single short syllable, a spoken sentence
# runs long; a clip shorter than this holds no word at all.
SITE_DURATION = DurationBounds(shortest_s=0.12, longest_s=20.0)


def evaluate(stats: ClipStats, bounds: DurationBounds = FORM_DURATION) -> list[str]:
    """Return a list of problems (empty = clip passes). Pure; no I/O."""
    problems: list[str] = []
    if not (bounds.shortest_s <= stats.duration_s <= bounds.longest_s):
        problems.append(f"duration {stats.duration_s:.2f}s outside [{bounds.shortest_s}, {bounds.longest_s}]")
    if stats.max_volume_db <= _SILENCE_CEILING_DB:
        problems.append(f"silent/near-silent (peak {stats.max_volume_db:.1f} dB)")
    if stats.max_volume_db >= FULL_SCALE_DB:
        problems.append(f"clipping (peak {stats.max_volume_db:.1f} dB)")
    return problems


def measure(key: str, path: Path) -> ClipStats:
    """Read duration (ffprobe) and peak level (ffmpeg volumedetect) for a clip."""
    duration = float(
        subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    )
    volumedetect = subprocess.run(
        ["ffmpeg", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True,
    ).stderr
    match = re.search(r"max_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", volumedetect)
    max_db = float(match.group(1)) if match else -999.0
    return ClipStats(key=key, duration_s=duration, max_volume_db=max_db)


class UndecodableClip(RuntimeError):
    """A clip that does not decode to sound: corrupt, empty, or not audio at all."""


def wave_stats(key: str, wave: bytes) -> ClipStats:
    """Duration and peak (dBFS) of a decoded clip. Pure: bytes in, stats out."""
    try:
        sound = read_float_wave(wave)
    except NotFloatWave as problem:
        raise UndecodableClip(f"{key}: {problem}") from problem
    return ClipStats(key=key, duration_s=sound.duration_s, max_volume_db=sound.peak_db)


def decoded_stats(key: str, clip: Path) -> ClipStats:
    """Decode the clip (afconvert) to float PCM and measure it."""
    try:
        return wave_stats(key, decoded_wave(clip))
    except DecodeFailed as problem:
        raise UndecodableClip(f"{key}: {problem}") from problem


def check_all(keys: list[str], audio_dir: Path) -> dict[str, list[str]]:
    """QA every expected clip; return {key: problems} for any that fail.

    A missing file is itself a failure — the mapping between dataset and audio
    must be complete.
    """
    failures: dict[str, list[str]] = {}
    for key in keys:
        path = audio_dir / f"{key}.m4a"
        if not path.exists():
            failures[key] = ["missing file"]
            continue
        problems = evaluate(measure(key, path))
        if problems:
            failures[key] = problems
    return failures
