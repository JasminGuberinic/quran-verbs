"""Tests for the recitation adapter, with the network replaced by a fake."""

import urllib.error
import urllib.request

import pytest

from fil.recitation import NotAudio, RecitationLibrary, RecitationMissing

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


def _not_found(url: str) -> bytes:
    raise urllib.error.HTTPError(url, 404, "Not Found", None, None)


def test_a_clip_the_source_does_not_have_is_reported_as_missing_not_cached(tmp_path, monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", lambda request, timeout: _not_found(request.full_url))
    library = RecitationLibrary(tmp_path / "site", cache=tmp_path / "cache")

    with pytest.raises(RecitationMissing):
        library.word(4, 1, 30)
    assert not (tmp_path / "cache").exists()


def test_other_http_failures_still_fail_the_build(tmp_path, monkeypatch):
    def unavailable(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 503, "Unavailable", None, None)
    monkeypatch.setattr(urllib.request, "urlopen", unavailable)

    with pytest.raises(urllib.error.HTTPError):
        RecitationLibrary(tmp_path / "site", cache=tmp_path / "cache").word(4, 1, 30)


def test_a_missing_word_clip_leaves_that_word_without_one_and_is_reported(tmp_path):
    from fil.stages import site

    def fetch(url: str) -> bytes:
        raise RecitationMissing(url)
    sound = site._Sound(sink=None, recitations=RecitationLibrary(tmp_path / "site", fetch=fetch,
                                                                 cache=tmp_path / "cache"))

    assert sound.word(4, 1, 30) is None
    assert sound.missing_words == ["4:1:30"]
