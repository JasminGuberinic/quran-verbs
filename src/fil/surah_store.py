"""The surahs' data file: read and validated on the way in.

    data/surahs.json   {"_about": …, "surahs": [{"number", "arabic", "transliteration", "english", "revelation", "ayat"}]}

Copied from the Tanzil Quran metadata (CC BY 3.0), the source the ayah numbering already rests on
(fil.quran_numbering). A small I/O adapter; what a surah must hold is decided in fil.surahs.model.
"""

from __future__ import annotations

import json
from pathlib import Path

from fil.quran_numbering import SURAH_AYAH_COUNTS
from fil.resources import SURAHS_JSON
from fil.surahs.model import InvalidSurahData, Surah


def load_surahs(path: Path = SURAHS_JSON) -> tuple[Surah, ...]:
    """All 114 surahs in order, each checked against the ayah numbering."""
    entries = json.loads(path.read_text(encoding="utf-8"))["surahs"]
    surahs = tuple(Surah(number=entry["number"], arabic=entry["arabic"], transliteration=entry["transliteration"],
                         english=entry["english"], revelation=entry["revelation"], ayah_count=entry["ayat"])
                   for entry in entries)
    if [surah.number for surah in surahs] != list(range(1, len(SURAH_AYAH_COUNTS) + 1)):
        raise InvalidSurahData(f"{path.name} must list surahs 1–{len(SURAH_AYAH_COUNTS)} in order")
    slugs = [surah.slug for surah in surahs]
    if len(set(slugs)) != len(slugs):
        raise InvalidSurahData(f"{path.name}: two surahs share a page name")
    return surahs
