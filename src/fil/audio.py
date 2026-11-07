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

import hashlib
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Protocol

from fil.pcm import FULL_SCALE_DB, FloatWave, read_float_wave, scaled, write_float_wave


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

# The site embeds every clip in its pages, and a published version is capped at 256 MB, so
# clips ship as small mono AAC: speech is 22 kHz synthetic and stays clear at 24 kb/s;
# recitation carries more (a reciter's voice, the room) and keeps 32 kb/s.
SPEECH_BITRATE = 24_000
RECITATION_BITRATE = 32_000


def compact_aac_command(source: Path, target: Path, bitrate: int) -> list[str]:
    """The afconvert call that encodes a clip as mono AAC at this bitrate."""
    return ["afconvert", "-f", "m4af", "-d", "aac", "-c", "1", "-b", str(bitrate),
            str(source), str(target)]


class DecodeFailed(RuntimeError):
    """afconvert could not decode a clip: it is corrupt, empty, or not audio."""


def decode_command(source: Path, target: Path) -> list[str]:
    """The afconvert call that decodes any clip to a 32-bit float WAV."""
    return ["afconvert", "-f", "WAVE", "-d", "LEF32", str(source), str(target)]


def decoded_wave(clip: Path) -> bytes:
    """The clip decoded to a 32-bit float WAV (fil.pcm reads it)."""
    with tempfile.TemporaryDirectory() as folder:
        wave = Path(folder) / "decoded.wav"
        result = subprocess.run(decode_command(clip, wave), capture_output=True, text=True)
        if result.returncode != 0 or not wave.is_file():
            raise DecodeFailed(f"afconvert could not decode {clip.name}: {result.stderr.strip()[-200:]}")
        return wave.read_bytes()


# Speech comes from the model and recitation from its source at their own levels, and an
# AAC encode can push a peak near full scale past it. A clip whose decoded peak reaches
# full scale would clip (the audio gate refuses it), so it is turned down to this peak;
# every other clip is left exactly as it is, so the rule never touches a clip that is fine.
TURNED_DOWN_PEAK_DB = -1.0
# The codec and the mono downmix move the peak a little, so the turned-down clip is
# measured again; it settles in one pass, rarely two.
_TURN_DOWN_PASSES = 3


def clipping_gain_db(peak_db: float) -> float:
    """The gain that brings a clipping peak down to TURNED_DOWN_PEAK_DB: zero for a clip that does not clip."""
    return 0.0 if peak_db < FULL_SCALE_DB else TURNED_DOWN_PEAK_DB - peak_db


def encode_compact(source: Path, target: Path, bitrate: int) -> None:
    """Encode the clip as compact mono AAC that never clips once decoded.

    The clip is made aside and moved into place only once it passes, so a cache never
    keeps a half-made or clipping clip.
    """
    with tempfile.TemporaryDirectory() as folder:
        encoded = Path(folder) / target.name
        _encode(source, encoded, bitrate)
        _turn_down_if_clipping(source, encoded, bitrate, Path(folder) / "quieter.wav")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(encoded, target)


def _turn_down_if_clipping(source: Path, encoded: Path, bitrate: int, quieter: Path) -> None:
    """Re-encode a clip that clips from its source, turned down, until it no longer does."""
    gain_db = clipping_gain_db(_decoded(encoded).peak_db)
    total_gain_db = 0.0
    for _ in range(_TURN_DOWN_PASSES):
        if gain_db == 0.0:
            return
        total_gain_db += gain_db
        quieter.write_bytes(write_float_wave(scaled(_decoded(source), total_gain_db)))
        _encode(quieter, encoded, bitrate)
        gain_db = clipping_gain_db(_decoded(encoded).peak_db)
    if gain_db != 0.0:
        raise RuntimeError(f"{encoded.name} still clips after {_TURN_DOWN_PASSES} passes")


def _encode(source: Path, target: Path, bitrate: int) -> None:
    subprocess.run(compact_aac_command(source, target, bitrate), check=True, capture_output=True)


def _decoded(clip: Path) -> FloatWave:
    return read_float_wave(decoded_wave(clip))


def compact_clip_name(content_key: str, bitrate: int) -> str:
    """A cache file name that changes with the bitrate, so a re-encode never reuses an old clip."""
    return f"{hashlib.sha1(content_key.encode()).hexdigest()}-{bitrate // 1000}k.m4a"


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
