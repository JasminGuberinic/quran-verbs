"""The nuance groups' data file: read and validated on the way in.

    data/nuance_groups.json   {"<slug>": {"title", "shared", "tellApart", "sources", "notes", "members": [...]}}

A small I/O adapter; what a group must hold is decided in fil.nuances.model.
"""

from __future__ import annotations

import json
from pathlib import Path

from fil.nuances.model import NuanceGroup, parse_groups
from fil.resources import NUANCE_GROUPS_JSON

_ABOUT = "_about"


def load_groups(path: Path = NUANCE_GROUPS_JSON) -> tuple[NuanceGroup, ...]:
    """Every group, validated (fil.nuances.model.InvalidNuanceData); none when there is no file."""
    if not path.exists():
        return ()
    entries = json.loads(path.read_text(encoding="utf-8"))
    return parse_groups({slug: entry for slug, entry in entries.items() if slug != _ABOUT})
