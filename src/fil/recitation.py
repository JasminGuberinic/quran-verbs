"""Real recitation clips — the adapter between the site and the audio it borrows.

Every clip a learner hears as "the Quran" is a human recitation, never a synthetic voice:
whole ayat by Mishary Alafasy (everyayah.com) and single words from quran.com's
word-by-word audio. Synthetic speech is left to the viewer's own browser, so nothing
machine-voiced is ever shipped as if it were recitation.

Clips are fetched once into a cache, and each is checked to really be audio before it
is used — a host that answers with an error page must fail the build, not ship silence.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path
from typing import Callable

from fil.resources import RECITATION_CACHE

# Fetch a URL's bytes. Injected so the site builder can be tested without the network.
Fetch = Callable[[str], bytes]

AYAH_SOURCE = "https://everyayah.com/data/Alafasy_64kbps/{surah:03d}{ayah:03d}.mp3"
WORD_SOURCE = "https://audio.qurancdn.com/wbw/{surah:03d}_{ayah:03d}_{word:03d}.mp3"


class NotAudio(ValueError):
    """A source answered with something that is not an MP3."""


def ayah_path(surah: int, ayah: int) -> str:
    return f"audio/ayah/{surah:03d}{ayah:03d}.mp3"


def word_path(surah: int, ayah: int, word: int) -> str:
    return f"audio/word/{surah:03d}_{ayah:03d}_{word:03d}.mp3"


class RecitationLibrary:
    """Puts the clips a page needs into its folder, downloading each at most once."""

    def __init__(self, site: Path, fetch: Fetch | None = None, cache: Path = RECITATION_CACHE):
        self._site = site
        self._fetch = fetch or _download
        self._cache = cache

    def ayah(self, surah: int, ayah: int) -> str:
        return self._place(AYAH_SOURCE.format(surah=surah, ayah=ayah), ayah_path(surah, ayah))

    def word(self, surah: int, ayah: int, word: int) -> str:
        return self._place(WORD_SOURCE.format(surah=surah, ayah=ayah, word=word),
                           word_path(surah, ayah, word))

    def _place(self, url: str, site_path: str) -> str:
        """Copy the clip into the site and return the path the page should load."""
        cached = self._cache / site_path
        if not cached.exists():
            clip = self._fetch(url)
            if not is_mp3(clip):
                raise NotAudio(f"{url} did not return audio")
            cached.parent.mkdir(parents=True, exist_ok=True)
            cached.write_bytes(clip)
        target = self._site / site_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(cached.read_bytes())
        return site_path


def is_mp3(clip: bytes) -> bool:
    """An MP3 starts with an ID3 tag or an MPEG frame sync."""
    return clip.startswith(b"ID3") or (len(clip) > 1 and clip[0] == 0xFF and clip[1] & 0xE0 == 0xE0)


def _download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "fil-study-site/0.1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()
