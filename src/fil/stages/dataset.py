"""The pipeline orchestrator: verbs.yaml -> conjugated dataset.

Run: `python build.py`. It reads the hand-authored verbs, generates each one's
full conjugation table, and writes a single JSON the later stages (audio, cards,
SQLite packaging, and eventually the iOS app) consume. Adding verbs never touches
this file — you only edit data/verbs.yaml.
"""

from __future__ import annotations

import json

import yaml

from fil.conjugation import conjugate
from fil.models import Verb
from fil.resources import BUILD_DIR, VERBS_YAML

_SOURCE = VERBS_YAML
_OUTPUT = BUILD_DIR / "verbs.json"


def load_verbs() -> list[Verb]:
    """Read and validate every verb block from verbs.yaml.

    Each block is validated (Verb.__post_init__), and ids must be unique — a
    duplicate id would otherwise silently overwrite another verb's audio clips.
    """
    raw = yaml.safe_load(_SOURCE.read_text(encoding="utf-8")) or []
    verbs = [_verb_from_block(block) for block in raw]
    _reject_duplicate_ids(verbs)
    return verbs


def _reject_duplicate_ids(verbs: list[Verb]) -> None:
    """Fail fast if two verbs share an id."""
    seen: set[str] = set()
    for verb in verbs:
        if verb.id in seen:
            raise ValueError(f"duplicate verb id: {verb.id!r}")
        seen.add(verb.id)


def _verb_from_block(block: dict) -> Verb:
    """Turn one YAML block into a validated Verb (fails loudly on bad input)."""
    return Verb(
        id=block["id"],
        root=block["root"],
        past3ms=block["past3ms"],
        present_vowel=block["present_vowel"],
        transitive=bool(block["transitive"]),
        form=int(block["form"]),
        glosses=dict(block["glosses"]),
        ayat=tuple(block.get("ayat") or ()),
    )


def build_verb(verb: Verb) -> dict:
    """Produce the full derived record for one verb."""
    return {
        "id": verb.id,
        "root": verb.root,
        "form": verb.form,
        "glosses": dict(verb.glosses),
        "past3ms": verb.past3ms,
        "ayat": list(verb.ayat),
        "conjugation": conjugate(verb),
    }


def main() -> None:
    """Build every verb and write the dataset, printing a short summary."""
    verbs = load_verbs()
    records = [build_verb(verb) for verb in verbs]

    _OUTPUT.parent.mkdir(exist_ok=True)
    _OUTPUT.write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Built {len(records)} verb(s) -> {_OUTPUT.relative_to(BUILD_DIR.parent)}")
    for record in records:
        cells = sum(len(t) for t in record["conjugation"].values())
        gloss = record["glosses"].get("en", next(iter(record["glosses"].values())))
        print(f"  {record['id']:12s} {gloss:12s} — {cells} forms")


if __name__ == "__main__":
    main()
