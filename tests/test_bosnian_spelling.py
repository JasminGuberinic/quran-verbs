"""Bosnian content spells Paradise and Hell as Besim Korkut does: Džennet, Džehennem.

The texts were written over many batches and drifted (Dženet, dženet, džehennem). Korkut capitalises
the nouns and doubles the n; the adjectives (džennetski, džehennemski) stay lowercase.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Any spelling of either word, with whatever inflection follows it.
PARADISE_OR_HELL = re.compile(r"[Dd][žz]e(?:n+et|h+en+em)\w*")
KORKUT_SPELLING = re.compile(r"Džennet(?!sk)\w*|Džehennem(?!sk)\w*|džennetsk\w*|džehennemsk\w*")

# Our own content; the corpus folders under data/ (qac, quranhive, translations) are third-party.
CONTENT_FILES = sorted(
    [*ROOT.glob("data/*.json"), *ROOT.glob("data/*.yaml"), *ROOT.glob("src/fil/**/*.js"), *ROOT.glob("src/fil/**/*.py")]
)


def variant_spellings(text: str) -> list[str]:
    """Every Paradise/Hell word in `text` that is not Korkut's spelling."""
    words = (match.group(0) for match in PARADISE_OR_HELL.finditer(text))
    return [word for word in words if not KORKUT_SPELLING.fullmatch(word)]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("u Džennet, stanovnici Dženneta, u Džennetu, Džennetom, u Džennetima", []),
        ("u Džehennem, u Džehennemu, džennetske bašče, džehennemski oganj", []),
        ("u Dženet", ["Dženet"]),
        ("stanovnici dženneta", ["dženneta"]),
        ("u Dženetu i u džehennem", ["Dženetu", "džehennem"]),
        ("dženetske bašče, Džennetske bašče, Džehenem", ["dženetske", "Džennetske", "Džehenem"]),
    ],
)
def test_variant_spellings_are_found(text: str, expected: list[str]) -> None:
    assert variant_spellings(text) == expected


def test_content_files_are_found() -> None:
    assert ROOT / "data" / "nuance_groups.json" in CONTENT_FILES


@pytest.mark.parametrize("path", CONTENT_FILES, ids=lambda path: str(path.relative_to(ROOT)))
def test_bosnian_content_spells_paradise_and_hell_as_korkut(path: Path) -> None:
    assert variant_spellings(path.read_text(encoding="utf-8")) == []
