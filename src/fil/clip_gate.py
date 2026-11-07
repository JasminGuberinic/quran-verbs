"""The site's audio gate: every clip it ships decodes, speaks, is long enough and never clips.

A file being there is not enough — a clip that is silent, cut off, corrupt or past full
scale must fail the build, not reach a learner (fil.audio_qa decides what each of those
means). The public site ships tens of thousands of clips, so measuring is cached: a
published clip is named by its content (fil.site_audio.published_name), and the same
name always holds the same sound, so its measurement never has to be taken twice. The
cache keeps the measurements, not the verdicts — a stricter rule judges every clip again
without decoding one.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Iterable, Mapping
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fil.audio_qa import SITE_DURATION, ClipStats, UndecodableClip, decoded_stats, evaluate

Measure = Callable[[str, Path], ClipStats]
_WORKERS = 8    # afconvert runs as a separate process, so decoding in threads really runs in parallel


class BrokenClip(RuntimeError):
    """A clip the site would ship fails the audio gate."""


def check_clips(clips: Iterable[Path], cache_file: Path, measure: Measure = decoded_stats) -> int:
    """Gate every clip (measuring only those the cache has not seen); return how many were measured.

    Raises BrokenClip naming every clip that fails, after the measurements it did take are cached.
    """
    clips = sorted(clips)
    known = read_cache(cache_file)
    unmeasured = [clip for clip in clips if clip.name not in known]
    measured, undecodable = measure_all(unmeasured, measure)
    write_cache(cache_file, {**known, **measured})
    stats = {**known, **measured}
    failures = {**undecodable, **{clip.name: problems for clip in clips if clip.name in stats and
                                  (problems := evaluate(stats[clip.name], SITE_DURATION))}}
    if failures:
        raise BrokenClip(_failure_report(failures))
    return len(unmeasured)


def measure_all(clips: list[Path], measure: Measure) -> tuple[dict[str, ClipStats], dict[str, list[str]]]:
    """Each clip's measurements, and the problem of each clip that would not decode."""
    with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
        outcomes = list(pool.map(lambda clip: _measured(clip, measure), clips))
    measured = {clip.name: outcome for clip, outcome in zip(clips, outcomes) if isinstance(outcome, ClipStats)}
    undecodable = {clip.name: [outcome] for clip, outcome in zip(clips, outcomes) if isinstance(outcome, str)}
    return measured, undecodable


def _measured(clip: Path, measure: Measure) -> ClipStats | str:
    try:
        return measure(clip.name, clip)
    except UndecodableClip as problem:
        return str(problem)


def read_cache(cache_file: Path) -> dict[str, ClipStats]:
    """The measurements taken before; an unreadable cache only means measuring again."""
    try:
        entries = json.loads(cache_file.read_text(encoding="utf-8"))
        return {name: ClipStats(key=name, duration_s=duration, max_volume_db=_peak(peak))
                for name, (duration, peak) in entries.items()}
    except (OSError, ValueError, TypeError):
        return {}


def write_cache(cache_file: Path, stats: Mapping[str, ClipStats]) -> None:
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    entries = {name: [clip.duration_s, None if math.isinf(clip.max_volume_db) else clip.max_volume_db]
               for name, clip in sorted(stats.items())}
    cache_file.write_text(json.dumps(entries, separators=(",", ":")), encoding="utf-8")


def _peak(stored: float | None) -> float:
    """JSON has no infinity: digital silence is stored as null."""
    return -math.inf if stored is None else float(stored)


def _failure_report(failures: Mapping[str, list[str]]) -> str:
    examples = "; ".join(f"{name}: {', '.join(problems)}" for name, problems in sorted(failures.items())[:5])
    return f"{len(failures)} clips fail the audio gate, e.g. {examples}"
