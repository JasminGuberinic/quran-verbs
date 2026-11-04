"""Where an ayah stands in the whole Quran: its number from 1 (1:1) to 6236 (114:6).

The streamed recitation (fil.recitation.AYAH_STREAM) names each ayah by this number, not
by surah and ayah. The surah lengths are the Tanzil Quran metadata
(https://tanzil.net/res/text/metadata/quran-data.js, © Tanzil Project, CC BY 3.0) — the
same Hafs numbering the corpus and every source we link to use.

Pure: two numbers in, one out.
"""

from __future__ import annotations

from itertools import accumulate

SURAH_AYAH_COUNTS: tuple[int, ...] = (
    7, 286, 200, 176, 120, 165, 206, 75, 129, 109, 123, 111, 43, 52, 99, 128, 111, 110, 98,
    135, 112, 78, 118, 64, 77, 227, 93, 88, 69, 60, 34, 30, 73, 54, 45, 83, 182, 88,
    75, 85, 54, 53, 89, 59, 37, 35, 38, 29, 18, 45, 60, 49, 62, 55, 78, 96, 29,
    22, 24, 13, 14, 11, 11, 18, 12, 12, 30, 52, 52, 44, 28, 28, 20, 56, 40, 31,
    50, 40, 46, 42, 29, 19, 36, 25, 22, 17, 19, 26, 30, 20, 15, 21, 11, 8, 8,
    19, 5, 8, 8, 11, 11, 8, 3, 9, 5, 4, 7, 3, 6, 3, 5, 4, 5, 6,
)
AYAH_TOTAL = 6236

# How many ayat come before each surah: 0 before al-Fatiha, 7 before al-Baqara, …
_AYAT_BEFORE = (0, *accumulate(SURAH_AYAH_COUNTS))


class NoSuchAyah(ValueError):
    """The Quran has no ayah at this surah and number."""


def ayah_number(surah: int, ayah: int) -> int:
    """The ayah's place in the whole Quran, counting from 1."""
    if not 1 <= surah <= len(SURAH_AYAH_COUNTS):
        raise NoSuchAyah(f"{surah}:{ayah}: there are {len(SURAH_AYAH_COUNTS)} surahs")
    if not 1 <= ayah <= SURAH_AYAH_COUNTS[surah - 1]:
        raise NoSuchAyah(f"{surah}:{ayah}: surah {surah} has {SURAH_AYAH_COUNTS[surah - 1]} ayat")
    return _AYAT_BEFORE[surah - 1] + ayah
