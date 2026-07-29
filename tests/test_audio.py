"""Tests for audio keying and the QA decision logic (no ffmpeg needed)."""

from fil.audio import clip_key
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
