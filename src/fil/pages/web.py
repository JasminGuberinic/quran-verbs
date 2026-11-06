"""The real network behind the deploy's ports (fil.pages.indexnow): one GET or one POST over urllib."""

from __future__ import annotations

import urllib.error
import urllib.request
from collections.abc import Mapping

_TIMEOUT_SECONDS = 30


def get(url: str) -> str:
    """The body of the page at `url` as text; raises OSError (urllib's errors are OSErrors) when none came."""
    with urllib.request.urlopen(url, timeout=_TIMEOUT_SECONDS) as response:
        return response.read().decode("utf-8")


def post(url: str, body: bytes, headers: Mapping[str, str]) -> int:
    """POST and return the status code; an HTTP error is an answer too, so it is returned, not raised."""
    request = urllib.request.Request(url, data=body, headers=dict(headers), method="POST")
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code
