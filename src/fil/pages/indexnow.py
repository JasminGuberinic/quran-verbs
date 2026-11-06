"""Tell IndexNow search engines (Bing, Yandex, Seznam, Naver, …) which pages just changed.

After a deploy the changed addresses are POSTed to api.indexnow.org, which shares them
with every participating engine. The engine proves the ping is ours by fetching the key
file we publish; the site lives in a subfolder (/quran-verbs/), so the request names the
key file's address (`keyLocation`) instead of relying on the host root.

The key is not a secret — it is published on the site by design; it only has to stay
the same from one deploy to the next.

The decision (which requests to send) is pure; the network sits behind the `HttpPost`
port, and a failed ping is reported, never raised: the site is already live by then.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Collection, Iterable, Mapping
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse

from fil.pages import seo

KEY = "d66ea097dffafa6511a406e8667931ad"
ENDPOINT = "https://api.indexnow.org/indexnow"
URLS_PER_REQUEST = 10_000      # the protocol's limit
_ACCEPTED = frozenset({200, 202})


class HttpPost(Protocol):
    def __call__(self, url: str, body: bytes, headers: Mapping[str, str]) -> int:
        """POST the body and return the response's status code (raise OSError if none came)."""


@dataclass(frozen=True)
class Submission:
    urls: tuple[str, ...]

    def body(self) -> bytes:
        return json.dumps({"host": urlparse(seo.SITE_URL).hostname, "key": KEY,
                           "keyLocation": key_location(), "urlList": list(self.urls)}).encode("utf-8")


def key_file_name() -> str:
    return f"{KEY}.txt"


def key_file_text() -> str:
    """What the published key file holds: the key, nothing else."""
    return KEY


def key_location() -> str:
    return seo.absolute(key_file_name())


def news(entries: Iterable[seo.SitemapEntry], changed_in_build: Collection[str],
         published: Mapping[str, str] | None) -> tuple[str, ...]:
    """The addresses to announce after a deploy, in sitemap order.

    Those this build changed, and — when the sitemap that was live before the deploy could
    be read (`published`: address → lastmod) — every address whose lastmod differs from it
    or that it did not list. The second part catches changes an earlier plain `fil pages`
    already recorded in the manifest but never deployed.
    """
    changed = frozenset(changed_in_build)
    return tuple(entry.url for entry in entries
                 if entry.url in changed
                 or (published is not None and published.get(entry.url) != entry.modified))


def submissions(urls: Iterable[str]) -> tuple[Submission, ...]:
    """The requests that announce these addresses, at most URLS_PER_REQUEST each."""
    addresses = tuple(urls)
    return tuple(Submission(addresses[start:start + URLS_PER_REQUEST])
                 for start in range(0, len(addresses), URLS_PER_REQUEST))


def ping(urls: Iterable[str], post: HttpPost, report: Callable[[str], None]) -> bool:
    """Announce the addresses; True when every request was accepted. Never raises on a failed request."""
    return all([_send(submission, post, report) for submission in submissions(urls)])


def _send(submission: Submission, post: HttpPost, report: Callable[[str], None]) -> bool:
    try:
        status = post(ENDPOINT, submission.body(), {"Content-Type": "application/json; charset=utf-8"})
    except OSError as error:
        report(f"IndexNow ping failed for {len(submission.urls)} addresses: {error}")
        return False
    if status not in _ACCEPTED:
        report(f"IndexNow refused {len(submission.urls)} addresses: HTTP {status}")
        return False
    report(f"IndexNow accepted {len(submission.urls)} addresses (HTTP {status})")
    return True


def is_key_live(body: str) -> bool:
    """The engines refuse a ping (HTTP 403) until the key file they fetch holds exactly our key."""
    return body.strip() == KEY
