"""Audio factory: turn each conjugated form into a clean, normalized clip.

Two ideas make this trustworthy for a religious app:

  1. Structural keying. A clip is named `<verb_id>__<tense>__<pronoun>.m4a`. The
     app looks up audio by the SAME key, so a clip can never be bound to the
     wrong form — the mapping is structural, not positional.
  2. Pluggable voice. The voice is a swappable provider. We ship a zero-setup
     placeholder (macOS `say`, Arabic voice "Majed"); for release we swap in a
     human reciter or a diacritic-aware neural TTS — nothing else changes.

Every clip is silence-trimmed and loudness-normalized (EBU R128) so playback is
consistent and free of gaps/clipping.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path
from typing import Protocol


class VoiceProvider(Protocol):
    """Anything that can speak vocalized Arabic text into an audio file."""

    def render(self, vocalized_text: str, out_path: Path) -> None:
        ...


class MacSayVoice:
    """Placeholder voice using macOS `say`. Not release quality — a stand-in that
    lets the whole factory run today with zero installs or accounts."""

    def __init__(self, voice: str = "Majed") -> None:
        self._voice = voice

    def render(self, vocalized_text: str, out_path: Path) -> None:
        subprocess.run(
            ["say", "-v", self._voice, "-o", str(out_path), vocalized_text],
            check=True,
            capture_output=True,
        )


def clip_key(verb_id: str, tense: str, pronoun: str) -> str:
    """The structural key that names a form's audio everywhere (pipeline + app)."""
    return f"{verb_id}__{tense}__{pronoun}"


# Trim leading silence, reverse + trim (= trailing), reverse back.
_TRIM = "silenceremove=start_periods=1:start_silence=0.08:start_threshold=-45dB:detection=peak"
_TRIM_FILTER = f"{_TRIM},areverse,{_TRIM},areverse"

# Peak-normalize each clip to this ceiling — deterministic and clip-free by
# construction (a target below 0 dBFS can never clip). This is the right tool for
# sub-second words, where loudnorm's ~3 s integration window is unreliable.
_PEAK_TARGET_DB = -3.0

# Below this the trimmed clip has effectively no speech — a failed render we
# refuse, rather than amplifying noise up to the target.
_SILENCE_FLOOR_DB = -40.0


def process_to_m4a(raw_audio: Path, out_m4a: Path) -> None:
    """Trim silence, peak-normalize to a safe ceiling, encode to mono AAC (iOS)."""
    with tempfile.TemporaryDirectory() as work:
        trimmed = Path(work) / "trimmed.wav"
        _run_ffmpeg(["-i", str(raw_audio), "-af", _TRIM_FILTER, str(trimmed)])

        peak_db = _measure_peak_db(trimmed)
        if peak_db <= _SILENCE_FLOOR_DB:
            raise RuntimeError(f"empty/silent render (peak {peak_db:.1f} dB): {out_m4a.name}")

        gain_db = _PEAK_TARGET_DB - peak_db
        _run_ffmpeg(
            ["-i", str(trimmed), "-af", f"volume={gain_db:.2f}dB",
             "-ac", "1", "-ar", "48000", "-c:a", "aac", "-b:a", "64k", str(out_m4a)]
        )
    if not out_m4a.exists():
        raise RuntimeError(f"ffmpeg did not produce {out_m4a.name}")


def _run_ffmpeg(args: list[str]) -> None:
    """Run ffmpeg quietly, raising with its error tail on failure."""
    result = subprocess.run(["ffmpeg", "-y", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr[-400:]}")


def _measure_peak_db(path: Path) -> float:
    """Read the sample peak (dBFS) of an audio file via ffmpeg's volumedetect."""
    stderr = subprocess.run(
        ["ffmpeg", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True,
    ).stderr
    match = re.search(r"max_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", stderr)
    if match is None:
        raise RuntimeError(f"could not measure peak level for {path.name}")
    return float(match.group(1))


def build_verb_audio(record: dict, provider: VoiceProvider, out_dir: Path) -> list[str]:
    """Generate every form's clip for one verb; return the keys produced."""
    out_dir.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        for tense, cells in record["conjugation"].items():
            for pronoun, form in cells.items():
                key = clip_key(record["id"], tense, pronoun)
                raw = Path(tmp) / f"{key}.aiff"
                provider.render(form, raw)
                process_to_m4a(raw, out_dir / f"{key}.m4a")
                keys.append(key)
    return keys
