"""The ayah-quotation gate over a data file: fil.ayah_quotes, wired to the file and the shipped English.

Run by `fil nuances check`, `fil particles check` and `fil pronouns check`, and by the tests, so a batch
that quotes an ayah in anyone's words but the shipped translation's (English) or our own (Bosnian)
never reaches a page.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fil import ayah_quotes
from fil.ayah_quotes import Reference

QUOTING_LANGUAGE = "en"


def problems_in(path: Path) -> list[str]:
    """Every quotation in the file that breaks the convention; empty when it may ship."""
    if not path.exists():
        return []
    entries = json.loads(path.read_text(encoding="utf-8"))
    return [f"{path.name} {problem}" for problem in ayah_quotes.problems(entries, shipped_english())]


@lru_cache(maxsize=1)
def shipped_english() -> dict[Reference, str]:
    """The English translation every page shows under an ayah — the only English an ayah is quoted in."""
    from fil.ayah_translations import AyahTranslations

    return AyahTranslations().texts(QUOTING_LANGUAGE)
