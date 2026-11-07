"""Fiʿl as an installable, offline-friendly web app (part of `fil pages`).

    manifest.webmanifest   name, start at the app's home, colours, icons
    sw.js                  the service worker (site/sw.js), with this build's id and the app shell filled in
    sw-routing.js          its routing decisions, a pure function the tests run under Node
    pwa.js                 registers the worker; guarded so it can never break a page
    icons/                 the app icons (site/icons, drawn by fil.pages.pwa_icons)

The worker's caches are named after the build id, a hash of everything the app shell is made of
plus the sitemap and the data, so a deploy that changes anything installs a fresh worker and the
old caches are deleted: a visitor is never held on stale content. (Content-named audio and
pictures never change, so their cache outlives builds.)
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

SITE_SOURCES = Path(__file__).resolve().parents[1] / "site"
BASE_PATH = "/quran-verbs/"            # where GitHub serves the project site
APP_START = BASE_PATH                  # the app's home, never the About page
MANIFEST_FILE = "manifest.webmanifest"
SERVICE_WORKER_FILE = "sw.js"
PWA_SCRIPT = "pwa.js"
ROUTING_SCRIPT = "sw-routing.js"
ICONS_FOLDER = "icons"
THEME_COLOUR = "#0f6b5c"               # --accent of site/pages.css
BACKGROUND_COLOUR = "#f2f5f3"          # --paper of site/pages.css
_SHELL_SUFFIXES = (".html", ".js", ".css", ".webmanifest")
_BUILD_INPUTS = ("sitemap.xml", "data.json")
_BUILD_PLACEHOLDER = "__BUILD__"
_SHELL_PLACEHOLDER = "__SHELL__"


def head_links(root: str) -> str:
    """The <head> lines every page carries; `root` is the path from the page to the site's root."""
    return (f'<link rel="manifest" href="{root}{MANIFEST_FILE}">\n'
            f'<meta name="theme-color" content="{THEME_COLOUR}">\n')


def manifest() -> dict:
    icon = f"{ICONS_FOLDER}/icon-{{}}.png"
    return {
        "id": APP_START,
        "name": "Fiʿl",
        "short_name": "Fiʿl",
        "description": "Verbs of the Quran: forms, ayat, audio and practice.",
        "start_url": APP_START,
        "scope": BASE_PATH,
        "display": "standalone",
        "theme_color": THEME_COLOUR,
        "background_color": BACKGROUND_COLOUR,
        "icons": [
            {"src": icon.format("192"), "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": icon.format("512"), "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": icon.format("maskable-512"), "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }


def write(pages: Path) -> None:
    """Publish the PWA files into an otherwise finished site (the shell and the build id are read from it)."""
    (pages / MANIFEST_FILE).write_text(json.dumps(manifest(), ensure_ascii=False, indent=2), encoding="utf-8")
    for name in (PWA_SCRIPT, ROUTING_SCRIPT):
        shutil.copyfile(SITE_SOURCES / name, pages / name)
    shutil.copytree(SITE_SOURCES / ICONS_FOLDER, pages / ICONS_FOLDER)
    (pages / SERVICE_WORKER_FILE).write_text(service_worker(pages), encoding="utf-8")


def shell_files(pages: Path) -> list[str]:
    """What the worker keeps for offline use from its first visit: the root's pages, scripts and styles."""
    names = sorted(path.name for path in pages.iterdir()
                   if path.is_file() and path.suffix in _SHELL_SUFFIXES and path.name != SERVICE_WORKER_FILE)
    return [*names, *(f"{ICONS_FOLDER}/{icon.name}" for icon in sorted((pages / ICONS_FOLDER).iterdir()))]


def build_id(pages: Path) -> str:
    """A hash of the shell, the sitemap and the data: it changes whenever anything a visitor sees may have."""
    digest = hashlib.sha256()
    for name in sorted({*shell_files(pages), *_BUILD_INPUTS}):
        digest.update(name.encode("utf-8"))
        digest.update((pages / name).read_bytes())
    return digest.hexdigest()[:12]


def service_worker(pages: Path) -> str:
    source = (SITE_SOURCES / SERVICE_WORKER_FILE).read_text(encoding="utf-8")
    for placeholder in (_BUILD_PLACEHOLDER, _SHELL_PLACEHOLDER):
        if source.count(placeholder) != 1:
            raise ValueError(f"site/{SERVICE_WORKER_FILE} must hold {placeholder} exactly once")
    return (source.replace(_BUILD_PLACEHOLDER, build_id(pages))
            .replace(_SHELL_PLACEHOLDER, json.dumps(shell_files(pages))))
