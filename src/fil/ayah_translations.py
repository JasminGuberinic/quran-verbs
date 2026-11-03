"""Translations of the ayat themselves — only ones free to use, never our own.

A practice sentence may be translated by a machine and labelled so; the Quran may not.
Under an ayah the learner sees a published translation whose author has been dead long
enough for it to be free, or the official translation of a state, credited by name.
Where a language has none (Bosnian and Albanian translations in digital form are all
still under copyright), the page falls back to English rather than to a guess.

The texts come from tanzil.net, which allows non-commercial use with a link back but not
re-publishing their collection — so they are fetched at build time into data/translations/
(git-ignored), like the corpus itself.
"""

from __future__ import annotations

import urllib.request
from dataclasses import dataclass
from pathlib import Path

from fil.resources import AYAH_TRANSLATIONS_DIR


@dataclass(frozen=True)
class Source:
    language: str
    tanzil_id: str
    credit: str          # shown under the translation, in the learner's view


SOURCES: tuple[Source, ...] = (
    Source("en", "en.pickthall", "M. M. Pickthall (1930), via tanzil.net"),
    Source("tr", "tr.yazir", "Elmalılı Hamdi Yazır, via tanzil.net"),
    Source("ur", "ur.kanzuliman", "احمد رضا خان، کنز الایمان · tanzil.net"),
    Source("id", "id.indonesian", "Kementerian Agama RI, via tanzil.net"),
    Source("ru", "ru.krachkovsky", "И. Ю. Крачковский (1963), via tanzil.net"),
)

FALLBACK = "en"

_URL = "https://tanzil.net/trans/?transID={id}&type=txt-2"


def parse(lines) -> dict[tuple[int, int], str]:
    """`sura|aya|text` lines → {(sura, aya): text}; comment and blank lines are skipped."""
    verses = {}
    for line in lines:
        line = line.rstrip("\n")
        if not line or line.startswith("#"):
            continue
        surah, ayah, text = line.split("|", 2)
        verses[(int(surah), int(ayah))] = text.strip()
    return verses


class AyahTranslations:
    """Every free translation we have, by language, loaded once."""

    def __init__(self, folder: Path = AYAH_TRANSLATIONS_DIR, fetch=None) -> None:
        self._verses = {source.language: parse(_lines(source, folder, fetch)) for source in SOURCES}
        self._credits = {source.language: source.credit for source in SOURCES}

    def of(self, surah: int, ayah: int) -> dict[str, dict[str, str]]:
        """{language: {"text", "by"}} for this ayah, in every language that has one."""
        return {
            language: {"text": verses[(surah, ayah)], "by": self._credits[language]}
            for language, verses in self._verses.items() if (surah, ayah) in verses
        }


def _lines(source: Source, folder: Path, fetch) -> list[str]:
    path = folder / f"{source.tanzil_id}.txt"
    if not path.exists():
        folder.mkdir(parents=True, exist_ok=True)
        path.write_bytes((fetch or _download)(_URL.format(id=source.tanzil_id)))
    lines = path.read_text(encoding="utf-8").splitlines()
    if sum(1 for line in lines if line and not line.startswith("#")) < 6000:
        raise ValueError(f"{path} does not look like a full translation (expected 6236 ayat)")
    return lines


def _download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "fil-study-site/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()
