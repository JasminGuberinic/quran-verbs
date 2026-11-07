"""The site's audio gate (fil.clip_gate), the float WAV it reads (fil.pcm) and the turn-down of a clipping clip (fil.audio)."""

import json
import math
import shutil
import subprocess
from pathlib import Path

import pytest

from fil.audio import (TURNED_DOWN_PEAK_DB, clipping_gain_db, compact_aac_command, decode_command, decoded_wave,
                       encode_compact)
from fil.audio_qa import SITE_DURATION, ClipStats, UndecodableClip, decoded_stats, evaluate, wave_stats
from fil.clip_gate import BrokenClip, check_clips, read_cache
from fil.pcm import FloatWave, NotFloatWave, read_float_wave, scaled, write_float_wave

_RATE = 22_050
_HAS_AFCONVERT = shutil.which("afconvert") is not None


def _tone(peak: float, seconds: float = 0.5, channels: int = 1) -> FloatWave:
    frames = int(_RATE * seconds)
    samples = [peak * math.sin(2 * math.pi * 220 * frame / _RATE) for frame in range(frames) for _ in range(channels)]
    return FloatWave(tuple(samples), channels, _RATE)


# ---------- fil.pcm: pure ----------

def test_a_float_wave_reads_back_what_was_written():
    sound = _tone(0.5, seconds=0.25, channels=2)
    again = read_float_wave(write_float_wave(sound))
    assert (again.channels, again.sample_rate, len(again.samples)) == (2, _RATE, len(sound.samples))
    assert again.duration_s == pytest.approx(0.25, abs=1e-3)
    assert again.peak_db == pytest.approx(20 * math.log10(0.5), abs=0.01)


def test_a_float_decode_shows_a_peak_past_full_scale():
    assert read_float_wave(write_float_wave(_tone(1.2))).peak_db > 0


def test_scaling_moves_the_peak_by_the_gain():
    assert scaled(_tone(1.0), -6.0).peak_db == pytest.approx(-6.0, abs=0.01)


def test_digital_silence_peaks_at_minus_infinity():
    assert FloatWave((0.0,) * 100, 1, _RATE).peak_db == -math.inf


@pytest.mark.parametrize("wave", [b"", b"not a wave at all", b"RIFF\x04\x00\x00\x00WAVE"])
def test_bytes_that_are_no_float_wave_are_refused(wave):
    with pytest.raises(NotFloatWave):
        read_float_wave(wave)


def test_a_clip_that_does_not_decode_is_undecodable_not_a_crash():
    with pytest.raises(UndecodableClip, match="clip-a"):
        wave_stats("clip-a", b"garbage")


# ---------- the site's limits ----------

def test_the_site_gate_passes_a_spoken_sentence_and_a_short_recited_word():
    assert evaluate(ClipStats("sentence", 7.5, -2.0), SITE_DURATION) == []
    assert evaluate(ClipStats("word", 0.3, -4.0), SITE_DURATION) == []


@pytest.mark.parametrize("stats, problem", [
    (ClipStats("k", 1.0, -math.inf), "silent"),
    (ClipStats("k", 1.0, -60.0), "silent"),
    (ClipStats("k", 0.05, -3.0), "duration"),
    (ClipStats("k", 1.0, 0.4), "clipping"),
])
def test_the_site_gate_refuses_silence_a_cut_off_clip_and_clipping(stats, problem):
    assert any(problem in found for found in evaluate(stats, SITE_DURATION))


# ---------- fil.clip_gate: the cache and the verdict ----------

class _CountingMeter:
    """Stands in for the decoder: measurements by file name, and how often each was taken."""

    def __init__(self, stats: dict[str, ClipStats | Exception]) -> None:
        self._stats = stats
        self.calls: list[str] = []

    def __call__(self, key: str, _clip: Path) -> ClipStats:
        self.calls.append(key)
        outcome = self._stats[key]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _clips(folder: Path, *names: str) -> list[Path]:
    for name in names:
        (folder / name).write_bytes(b"m4a")
    return [folder / name for name in names]


def test_a_clip_is_measured_once_and_judged_from_the_cache_after(tmp_path):
    clips = _clips(tmp_path, "a.m4a", "b.m4a")
    meter = _CountingMeter({"a.m4a": ClipStats("a.m4a", 1.0, -3.0), "b.m4a": ClipStats("b.m4a", 0.5, -math.inf)})
    cache = tmp_path / "qa.json"

    with pytest.raises(BrokenClip, match="b.m4a: silent"):
        check_clips(clips, cache, meter)
    assert check_clips(clips[:1], cache, meter) == 0

    assert meter.calls == ["a.m4a", "b.m4a"]
    assert read_cache(cache)["b.m4a"].max_volume_db == -math.inf    # silence survives JSON as null


def test_every_failing_clip_is_named_and_an_undecodable_one_fails_too(tmp_path):
    clips = _clips(tmp_path, "good.m4a", "loud.m4a", "broken.m4a")
    meter = _CountingMeter({"good.m4a": ClipStats("good.m4a", 1.0, -3.0),
                            "loud.m4a": ClipStats("loud.m4a", 1.0, 0.2),
                            "broken.m4a": UndecodableClip("broken.m4a: afconvert could not decode it")})
    with pytest.raises(BrokenClip) as failure:
        check_clips(clips, tmp_path / "qa.json", meter)
    assert str(failure.value).startswith("2 clips fail the audio gate")
    assert "loud.m4a: clipping" in str(failure.value) and "broken.m4a" in str(failure.value)


def test_an_unreadable_cache_only_means_measuring_again(tmp_path):
    clips = _clips(tmp_path, "a.m4a")
    cache = tmp_path / "qa.json"
    cache.write_text("{not json", encoding="utf-8")
    meter = _CountingMeter({"a.m4a": ClipStats("a.m4a", 1.0, -3.0)})
    assert check_clips(clips, cache, meter) == 1
    assert json.loads(cache.read_text(encoding="utf-8")) == {"a.m4a": [1.0, -3.0]}


def test_a_stricter_rule_judges_cached_clips_again_without_decoding(tmp_path):
    clips = _clips(tmp_path, "a.m4a")
    cache = tmp_path / "qa.json"
    cache.write_text(json.dumps({"a.m4a": [0.01, -3.0]}), encoding="utf-8")    # measured, now too short
    meter = _CountingMeter({})
    with pytest.raises(BrokenClip, match="duration"):
        check_clips(clips, cache, meter)
    assert meter.calls == []


# ---------- turning down a clip that clips ----------

def test_only_a_clip_that_clips_is_turned_down_and_then_to_minus_one_dbfs():
    assert clipping_gain_db(-3.0) == 0.0
    assert clipping_gain_db(-0.01) == 0.0
    assert clipping_gain_db(0.0) == pytest.approx(TURNED_DOWN_PEAK_DB)
    assert clipping_gain_db(0.4) == pytest.approx(TURNED_DOWN_PEAK_DB - 0.4)


def test_decoding_is_to_32_bit_float():
    assert decode_command(Path("in.m4a"), Path("out.wav"))[:5] == ["afconvert", "-f", "WAVE", "-d", "LEF32"]


@pytest.mark.skipif(not _HAS_AFCONVERT, reason="afconvert (macOS) is not installed")
def test_a_clip_past_full_scale_is_encoded_turned_down_to_about_minus_one_dbfs(tmp_path):
    loud = tmp_path / "loud.wav"
    loud.write_bytes(write_float_wave(_tone(1.3)))
    encode_compact(loud, tmp_path / "loud.m4a", 24_000)
    assert -2.0 < decoded_stats("loud", tmp_path / "loud.m4a").max_volume_db < 0.0


@pytest.mark.skipif(not _HAS_AFCONVERT, reason="afconvert (macOS) is not installed")
def test_a_clip_that_does_not_clip_is_encoded_as_it_is(tmp_path):
    quiet = tmp_path / "quiet.wav"
    quiet.write_bytes(write_float_wave(_tone(0.8)))
    encode_compact(quiet, tmp_path / "quiet.m4a", 24_000)
    subprocess.run(compact_aac_command(quiet, tmp_path / "plain.m4a", 24_000), check=True, capture_output=True)
    assert decoded_wave(tmp_path / "quiet.m4a") == decoded_wave(tmp_path / "plain.m4a")
