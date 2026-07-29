"""Audio QA gate: catch wrong/missing/glitchy clips before they ship.

The decision logic (`evaluate`) is a pure function of measured stats, so it is
unit-testable without touching ffmpeg. `measure` does the ffmpeg/ffprobe reads.
For a religious app this gate is non-negotiable: a silent, truncated, or clipped
clip must fail the build, not reach a learner.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

# Acceptable bounds for a single spoken verb form.
_MIN_DURATION_S = 0.2
_MAX_DURATION_S = 3.0
# Peak below this is effectively silence (a failed/empty render).
_SILENCE_CEILING_DB = -50.0
# Clipping is reaching full scale (0 dBFS); a peak below 0 is not clipping.
_CLIPPING_DB = 0.0


@dataclass(frozen=True)
class ClipStats:
    """What we measure about one produced clip."""

    key: str
    duration_s: float
    max_volume_db: float


def evaluate(stats: ClipStats) -> list[str]:
    """Return a list of problems (empty = clip passes). Pure; no I/O."""
    problems: list[str] = []
    if not (_MIN_DURATION_S <= stats.duration_s <= _MAX_DURATION_S):
        problems.append(f"duration {stats.duration_s:.2f}s outside [{_MIN_DURATION_S}, {_MAX_DURATION_S}]")
    if stats.max_volume_db <= _SILENCE_CEILING_DB:
        problems.append(f"silent/near-silent (peak {stats.max_volume_db:.1f} dB)")
    if stats.max_volume_db >= _CLIPPING_DB:
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
