"""Real recitation — the adapter between the site and the human voices it borrows.

Every clip a learner hears as "the Quran" is a human recitation, never a synthetic voice.
Each comes from a source whose published terms allow what we do with it:

  - whole ayat, recited by Mishary Rashid Alafasy, are streamed from the Islamic Network
    CDN behind alquran.cloud when the learner presses play — their terms allow streaming and
    embedding for educational use, not re-hosting, so no ayah recitation is ever shipped;
  - single words come from the QuranHive Word-by-Word Audio Dataset (© QuranHive, CC BY
    4.0), one archive downloaded once into data/quranhive/ (git-ignored). Its files are
    named surah_ayah_word, numbered exactly as the corpus numbers its words: all 77,425
    words of their mapping match ours letter for letter (THIRD_PARTY_NOTICES.md tells how
    this was checked). Only 1:1 is not in the dataset; no verb stands there.

A word clip is taken out of the archive once into a cache, and is checked to really be
audio before it is used. A word the archive does not have is a different case: it is
reported as RecitationMissing so the caller can show that word without a recited clip.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Protocol

from fil.quran_numbering import ayah_number

# The address of an ayah's recitation, by its number in the whole Quran (1..6236). 64 kb/s
# is one of the bitrates the CDN publishes for this reciter (as is 128).
AYAH_STREAM = "https://cdn.islamic.network/quran/audio/64/ar.alafasy/{number}.mp3"

WORD_ARCHIVE_URL = ("https://huggingface.co/datasets/quranhive/quran_word_by_word_audio/"
                    "resolve/main/qh-quran-word-audio-files.zip")
_ARCHIVE_FOLDER = "qh-quran-word-audio-files"


class NotAudio(ValueError):
    """A source gave something that is not an MP3."""


class RecitationMissing(LookupError):
    """The source has no clip for this word."""


class WordArchiveMissing(FileNotFoundError):
    """The QuranHive archive has not been downloaded yet."""


def ayah_stream(surah: int, ayah: int) -> str:
    """Where the learner's browser fetches an ayah's recitation from."""
    return AYAH_STREAM.format(number=ayah_number(surah, ayah))


def is_streamed(reference: str) -> bool:
    """Whether a sound reference is an ayah streamed from its source rather than a file of ours."""
    return reference.startswith(AYAH_STREAM.split("{", 1)[0])


def word_clip_name(surah: int, ayah: int, word: int) -> str:
    """The dataset's own name for a word's clip: 002_255_001.mp3."""
    return f"{surah:03d}_{ayah:03d}_{word:03d}.mp3"


class WordClipSource(Protocol):
    def clip(self, name: str) -> bytes:
        """The clip's bytes; RecitationMissing when the source has none by that name."""


class QuranHiveArchive:
    """The dataset's single zip, read in place — 77,425 clips need not be unpacked to use a few thousand."""

    def __init__(self, archive: Path) -> None:
        self._archive = archive
        self._zip: zipfile.ZipFile | None = None

    def clip(self, name: str) -> bytes:
        try:
            return self._opened().read(f"{_ARCHIVE_FOLDER}/{name}")
        except KeyError as error:
            raise RecitationMissing(f"{name} is not in {self._archive.name}") from error

    def _opened(self) -> zipfile.ZipFile:
        if self._zip is None:
            if not self._archive.is_file():
                raise WordArchiveMissing(
                    f"{self._archive} is missing. Download the QuranHive word audio (CC BY 4.0, ~1.6 GB):\n"
                    f"  mkdir -p {self._archive.parent} && curl -sSfL -o {self._archive} {WORD_ARCHIVE_URL}")
            self._zip = zipfile.ZipFile(self._archive)
        return self._zip


class WordRecitations:
    """Each word's recited clip as a file, taken from the source at most once."""

    def __init__(self, source: WordClipSource, cache: Path) -> None:
        self._source = source
        self._cache = cache

    def word(self, surah: int, ayah: int, word: int) -> Path:
        cached = self._cache / word_clip_name(surah, ayah, word)
        if cached.exists():
            return cached
        clip = self._source.clip(cached.name)
        if not is_mp3(clip):
            raise NotAudio(f"{cached.name} is not audio")
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(clip)
        return cached


def is_mp3(clip: bytes) -> bool:
    """An MP3 starts with an ID3 tag or an MPEG frame sync."""
    return clip.startswith(b"ID3") or (len(clip) > 1 and clip[0] == 0xFF and clip[1] & 0xE0 == 0xE0)
