"""Persist the public pages' versions (fil.pages.freshness) in the committed data/page_versions.json.

Committed so every machine that builds the site dates pages the same way: a page's
`<lastmod>` follows its content, not whoever built it last. Written sorted,
one page per line (see `save`).
"""

from __future__ import annotations

import json
from pathlib import Path

from fil.pages.freshness import Manifest, PageVersion
from fil.resources import PAGE_VERSIONS_JSON


def load(path: Path = PAGE_VERSIONS_JSON) -> dict[str, PageVersion]:
    """Every recorded page version (empty before the first build)."""
    if not path.exists():
        return {}
    return {address: PageVersion(entry["fingerprint"], entry["modified"])
            for address, entry in json.loads(path.read_text(encoding="utf-8")).items()}


def save(manifest: Manifest, path: Path = PAGE_VERSIONS_JSON) -> None:
    """One line per page, sorted: a build that changed three pages is a three-line diff."""
    lines = [f"{json.dumps(address, ensure_ascii=False)}: "
             f"{json.dumps({'fingerprint': version.fingerprint, 'modified': version.modified})}"
             for address, version in sorted(manifest.items())]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{\n" + ",\n".join(lines) + "\n}\n" if lines else "{}\n", encoding="utf-8")
