"""When each public page last really changed: the `<lastmod>` the sitemap gives it.

A build rewrites every page, so a file's own date says nothing. Instead each sitemap page
is fingerprinted — a hash of its HTML with the volatile parts blanked out — and the
fingerprint is compared with the one recorded in the committed manifest
(data/page_versions.json). A page keeps its recorded date while its fingerprint holds;
a changed or new page is dated the day of the build (UTC); a page that left the sitemap
leaves the manifest. Search engines trust a `<lastmod>` only while it is honest, so a
rebuild of unchanged content must never move it.

Volatile: the name of a published sound (`audio/<content hash>.m4a`). A clip that is
re-encoded or re-synthesized gets a new name without the page teaching anything new.

Pure functions; the manifest is read and written by fil.page_version_store.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass

_PUBLISHED_SOUND = re.compile(r"audio/[0-9a-f]+\.m4a")
_SOUND_PLACEHOLDER = "audio/~.m4a"
_FINGERPRINT_LENGTH = 32     # 128 bits: no two versions of a page will ever collide
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass(frozen=True)
class PageVersion:
    fingerprint: str
    modified: str        # YYYY-MM-DD, UTC

    def __post_init__(self) -> None:
        if not _ISO_DATE.fullmatch(self.modified):
            raise ValueError(f"a page's date must be YYYY-MM-DD, not {self.modified!r}")


Manifest = Mapping[str, PageVersion]     # page address → its version


def fingerprint(html: str) -> str:
    """The hash of what the page says, blind to the parts that change without it changing."""
    meaningful = _PUBLISHED_SOUND.sub(_SOUND_PLACEHOLDER, html)
    return hashlib.sha256(meaningful.encode("utf-8")).hexdigest()[:_FINGERPRINT_LENGTH]


def update(recorded: Manifest, fingerprints: Mapping[str, str], today: str) -> dict[str, PageVersion]:
    """The manifest after a build: exactly the built pages, each dated by its last real change."""
    return {address: _version(recorded.get(address), page_fingerprint, today)
            for address, page_fingerprint in sorted(fingerprints.items())}


def changed(recorded: Manifest, current: Manifest) -> tuple[str, ...]:
    """The pages this build changed or added, in address order — those whose date it set.

    Compared by fingerprint, not date: a page changed twice on one day keeps its date the
    second time, yet still has news for the search engines.
    """
    return tuple(address for address, version in sorted(current.items())
                 if address not in recorded or recorded[address].fingerprint != version.fingerprint)


def _version(recorded: PageVersion | None, page_fingerprint: str, today: str) -> PageVersion:
    if recorded is not None and recorded.fingerprint == page_fingerprint:
        return recorded
    return PageVersion(page_fingerprint, today)
