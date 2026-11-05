"""Tests for the recitation adapter: the streamed ayat and the QuranHive word clips."""

import zipfile

import pytest

from fil.recitation import (AYAH_STREAM, NotAudio, QuranHiveArchive, RecitationMissing, WordArchiveMissing,
                            WordRecitations, ayah_stream, word_clip_name)

_MP3 = b"ID3" + b"\x00" * 20


class _FakeSource:
    def __init__(self, clips: dict[str, bytes]) -> None:
        self.clips = clips
        self.asked: list[str] = []

    def clip(self, name: str) -> bytes:
        self.asked.append(name)
        if name not in self.clips:
            raise RecitationMissing(name)
        return self.clips[name]


def test_an_ayah_streams_from_the_alquran_cloud_cdn_by_its_number_in_the_quran():
    assert ayah_stream(2, 255) == "https://cdn.islamic.network/quran/audio/64/ar.alafasy/262.mp3"
    assert ayah_stream(114, 6).endswith("/6236.mp3")
    assert "everyayah" not in AYAH_STREAM


def test_a_word_clip_is_named_as_the_dataset_names_it():
    assert word_clip_name(2, 255, 1) == "002_255_001.mp3"
    assert word_clip_name(114, 6, 3) == "114_006_003.mp3"


def test_a_word_clip_is_taken_from_the_source_once_and_cached(tmp_path):
    source = _FakeSource({"001_005_002.mp3": _MP3})
    words = WordRecitations(source, tmp_path / "cache")

    first = words.word(1, 5, 2)
    again = words.word(1, 5, 2)

    assert first == again == tmp_path / "cache" / "001_005_002.mp3"
    assert first.read_bytes() == _MP3
    assert source.asked == ["001_005_002.mp3"]


def test_something_that_is_not_audio_fails_the_build(tmp_path):
    # Shipping a broken file as "recitation" would play silence to a learner.
    words = WordRecitations(_FakeSource({"007_015_001.mp3": b"<html>404</html>"}), tmp_path / "cache")

    with pytest.raises(NotAudio):
        words.word(7, 15, 1)


def test_a_word_the_source_does_not_have_is_missing_and_not_cached(tmp_path):
    words = WordRecitations(_FakeSource({}), tmp_path / "cache")

    with pytest.raises(RecitationMissing):
        words.word(1, 1, 1)
    assert not (tmp_path / "cache").exists()


def _archive(path, names):
    with zipfile.ZipFile(path, "w") as archive:
        for name in names:
            archive.writestr(f"qh-quran-word-audio-files/{name}", _MP3)
    return path


def test_the_quranhive_archive_is_read_in_place(tmp_path):
    archive = QuranHiveArchive(_archive(tmp_path / "qh.zip", ["002_255_001.mp3"]))

    assert archive.clip("002_255_001.mp3") == _MP3
    with pytest.raises(RecitationMissing):
        archive.clip("001_001_001.mp3")


def test_a_missing_archive_says_how_to_download_it(tmp_path):
    with pytest.raises(WordArchiveMissing, match="curl .*huggingface.co/datasets/quranhive"):
        QuranHiveArchive(tmp_path / "absent.zip").clip("002_255_001.mp3")


def test_a_missing_word_clip_leaves_that_word_without_one_and_is_reported(tmp_path):
    from fil.stages import site

    sound = site.Sound(sink=None, recitations=WordRecitations(_FakeSource({}), tmp_path / "cache"))

    assert sound.word(4, 1, 30) is None
    assert sound.missing_words == ["4:1:30"]
    assert sound.ayah(4, 1) == AYAH_STREAM.format(number=494)
