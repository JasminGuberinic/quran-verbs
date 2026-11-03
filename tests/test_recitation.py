"""Tests for the recitation adapter, with the network replaced by a fake."""

import pytest

from fil.recitation import NotAudio, RecitationLibrary

_MP3 = b"ID3" + b"\x00" * 20


def test_a_clip_is_fetched_once_and_placed_in_the_site(tmp_path):
    fetched = []
    library = RecitationLibrary(tmp_path / "site", fetch=lambda url: fetched.append(url) or _MP3,
                                cache=tmp_path / "cache")

    first = library.ayah(1, 5)
    library.ayah(1, 5)

    assert first == "audio/ayah/001005.mp3"
    assert (tmp_path / "site" / first).read_bytes() == _MP3
    assert fetched == ["https://everyayah.com/data/Alafasy_64kbps/001005.mp3"]


def test_an_error_page_instead_of_audio_fails_the_build(tmp_path):
    # Shipping an HTML error page as "recitation" would play silence to a learner.
    library = RecitationLibrary(tmp_path / "site", fetch=lambda url: b"<html>404</html>",
                                cache=tmp_path / "cache")

    with pytest.raises(NotAudio):
        library.word(7, 15, 1)
