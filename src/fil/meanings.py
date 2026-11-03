"""What each studied verb means, in every learner language.

The catalogue knows a verb's root, form and every place it occurs — but not what it
means. Meanings are authored here, one entry per verb, and this file is also the list of
verbs the study site covers: adding a batch of verbs to the site means adding their
meanings.

Loading fails fast on a missing language. A verb that silently lacks Turkish would show
a learner an empty card; the build should refuse instead.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from fil.languages import CODES
from fil.resources import MEANINGS_JSON


@dataclass(frozen=True)
class VerbMeaning:
    root: str
    form: int
    glosses: tuple[tuple[str, str], ...]   # (language code, meaning)

    def gloss(self, language: str) -> str:
        return next(text for code, text in self.glosses if code == language)


class MissingMeaning(ValueError):
    """A verb's meaning is missing in a language the site promises."""


def load(path: Path = MEANINGS_JSON, languages: tuple[str, ...] = CODES) -> list[VerbMeaning]:
    """Every authored meaning, in file order, each complete in every language."""
    if not path.exists():
        return []
    entries = json.loads(path.read_text(encoding="utf-8"))
    return [_meaning(key, glosses, languages) for key, glosses in entries.items()]


def _meaning(key: str, glosses: dict[str, str], languages: tuple[str, ...]) -> VerbMeaning:
    missing = [code for code in languages if not glosses.get(code, "").strip()]
    if missing:
        raise MissingMeaning(f"{key}: no meaning in {', '.join(missing)}")
    root, form = key.rsplit("_", 1)
    return VerbMeaning(root, int(form), tuple((code, glosses[code]) for code in languages))
