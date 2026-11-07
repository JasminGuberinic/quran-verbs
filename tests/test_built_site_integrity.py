"""Every built page has real content, and every file it points at exists.

A page with nothing on it, or a picture, drawing, script or clip that is not there, looks broken
to a learner; this gate fails the deploy before either can reach the site.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import unquote

import pytest

from fil.resources import PAGES_DIR

SITE_ROOT = "/quran-verbs/"
MIN_WORDS = 30
_SEARCH_ENGINE_PROOF = re.compile(r"^google[0-9a-f]+\.html$")
_LOCAL_REFERENCE = re.compile(r'(?:src|href|data-audio)="([^"#?]+)')
_MARKUP = re.compile(r"<script.*?</script>|<style.*?</style>|<[^>]+>", re.S)
_NOT_A_FILE = ("http:", "https:", "mailto:", "data:", "javascript:", "//")
_TEMPLATE = "${"   # a JavaScript template literal inside the app's script, filled at run time

built = pytest.mark.skipif(not (PAGES_DIR / "index.html").exists(), reason="run `fil pages` first")


def built_pages() -> list[Path]:
    return [page for page in PAGES_DIR.rglob("*.html") if not _SEARCH_ENGINE_PROOF.match(page.name)]


def visible_word_count(html: str) -> int:
    return len(_MARKUP.sub(" ", html).split())


def local_references(page: Path, html: str) -> Iterator[str]:
    for reference in _LOCAL_REFERENCE.findall(html):
        if reference.startswith(_NOT_A_FILE) or _TEMPLATE in reference:
            continue
        yield reference


def target_of(page: Path, reference: str) -> Path:
    if reference.startswith(SITE_ROOT):
        return PAGES_DIR / unquote(reference[len(SITE_ROOT):])
    return (page.parent / unquote(reference)).resolve()


def exists_on_site(target: Path) -> bool:
    return target.is_file() or (target / "index.html").is_file()


@built
def test_every_built_page_has_real_content():
    thin = [f"{page.relative_to(PAGES_DIR)} ({words} words)" for page in built_pages()
            if (words := visible_word_count(page.read_text(encoding="utf-8"))) < MIN_WORDS]
    assert not thin, f"{len(thin)} pages are nearly empty, e.g. {thin[:5]}"


@built
def test_every_local_link_picture_script_and_clip_exists():
    broken: dict[str, str] = {}
    for page in built_pages():
        html = page.read_text(encoding="utf-8")
        for reference in local_references(page, html):
            if not exists_on_site(target_of(page, reference)):
                broken.setdefault(reference, str(page.relative_to(PAGES_DIR)))
    assert not broken, f"{len(broken)} local references lead nowhere, e.g. {list(broken.items())[:5]}"


def test_a_template_literal_and_an_external_address_are_not_files():
    page = PAGES_DIR / "en" / "index.html"
    html = '<a href="${language}/about/"></a><img src="https://example.org/a.png"><a href="a/">'
    assert list(local_references(page, html)) == ["a/"]


def test_markup_scripts_and_styles_are_not_counted_as_words():
    assert visible_word_count("<style>a{b:c}</style><script>var x = 1;</script><p>one two</p>") == 2
