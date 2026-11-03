"""Tests for audio keying and the QA decision logic (no ffmpeg needed)."""

from pathlib import Path

from fil.audio import clip_key, compact_aac_command, compact_clip_name
from fil.audio_qa import ClipStats, evaluate


def test_clip_key_is_structural():
    # The key is derived purely from coordinates, so audio can't be mis-bound.
    assert clip_key("k-t-b_I", "past", "huwa") == "k-t-b_I__past__huwa"
    assert clip_key("n-s-r_I", "imperative", "anta") == "n-s-r_I__imperative__anta"


def test_qa_accepts_a_good_clip():
    good = ClipStats(key="k", duration_s=0.7, max_volume_db=-3.0)
    assert evaluate(good) == []


def test_qa_rejects_silence():
    silent = ClipStats(key="k", duration_s=0.7, max_volume_db=-70.0)
    problems = evaluate(silent)
    assert any("silent" in p for p in problems)


def test_qa_rejects_clipping():
    clipped = ClipStats(key="k", duration_s=0.7, max_volume_db=0.0)
    assert any("clipping" in p for p in evaluate(clipped))


def test_qa_rejects_out_of_band_duration():
    too_long = ClipStats(key="k", duration_s=9.0, max_volume_db=-3.0)
    too_short = ClipStats(key="k", duration_s=0.05, max_volume_db=-3.0)
    assert any("duration" in p for p in evaluate(too_long))
    assert any("duration" in p for p in evaluate(too_short))


def test_compact_clips_are_mono_aac_at_the_requested_bitrate():
    command = compact_aac_command(Path("in.wav"), Path("out.m4a"), 24_000)

    assert command[:5] == ["afconvert", "-f", "m4af", "-d", "aac"]
    assert command[command.index("-c") + 1] == "1"
    assert command[command.index("-b") + 1] == "24000"
    assert command[-2:] == ["in.wav", "out.m4a"]


def test_a_new_bitrate_never_reuses_a_clip_cached_at_the_old_one():
    assert compact_clip_name("qul", 24_000) != compact_clip_name("qul", 48_000)
    assert compact_clip_name("qul", 24_000) == compact_clip_name("qul", 24_000)
    assert compact_clip_name("qul", 24_000).endswith("-24k.m4a")
