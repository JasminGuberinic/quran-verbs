"""Gates over the built site (build/pages): every page is safe to read through a browser's page
translation. Read with the standard HTML parser, independently of fil.pages.untranslated:

  - every Arabic word sits inside an element marked translate="no" — except, on a Persian or
    Urdu page, the reader's own language, which is written in the same script;
  - every transliteration (Fiʿl, iḍāfa) sits inside one too;
  - every element in Arabic says lang="ar" dir="rtl", and every translate="no" carries the class
    `notranslate` that older Google Translate reads;
  - every ayah translation we quote (Pickthall, Tanzil's, our own) is marked translate="no";
  - every page names its language: <html lang> is the language of its folder.

Skipped until `fil pages` has built the site.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

import pytest

from fil.languages import LANGUAGES
from fil.resources import PAGES_DIR

_ARABIC_SCRIPT = re.compile("[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-ﻼ]")
_TRANSLITERATION = re.compile("[āīūḥḍṣṭẓʿʾĀĪŪḤḌṢṬẒ]")
_READERS_ARABIC_SCRIPT = frozenset({"fa", "ur"})
_VOID = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"})
_NOT_READ_AS_WORDS = frozenset({"script", "style", "textarea", "title", "head"})
_QUOTED_AYAH_TRANSLATIONS = frozenset({"translation", "ayah-translation"})   # the classes of a quoted ayah translation

built = pytest.mark.skipif(not (PAGES_DIR / "bs" / "index.html").is_file(), reason="build/pages not built (fil pages)")


@dataclass
class _Open:
    tag: str
    language: str
    is_untranslated: bool


@dataclass
class _Reader(HTMLParser):
    """Walks one page and records every way it would let a browser translate what it must not."""
    problems: list[str] = field(default_factory=list)
    page_language: str = ""
    open: list[_Open] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__init__(convert_charrefs=True)

    def handle_starttag(self, tag: str, attributes: list[tuple[str, str | None]]) -> None:
        values = {name: value or "" for name, value in attributes}
        outer = self.open[-1] if self.open else _Open("", "", False)
        if tag == "html":
            self.page_language = values.get("lang", "")
        self._check_element(tag, values, outer)
        if tag in _VOID:
            return
        self.open.append(_Open(tag, values.get("lang") or outer.language,
                               outer.is_untranslated or values.get("translate") == "no"))

    def handle_startendtag(self, tag: str, attributes: list[tuple[str, str | None]]) -> None:
        self._check_element(tag, {name: value or "" for name, value in attributes}, self.open[-1] if self.open else _Open("", "", False))

    def handle_endtag(self, tag: str) -> None:
        while self.open:
            if self.open.pop().tag == tag:
                return

    def handle_data(self, data: str) -> None:
        if any(element.tag in _NOT_READ_AS_WORDS for element in self.open):
            return
        context = self.open[-1] if self.open else _Open("", self.page_language, False)
        if context.is_untranslated:
            return
        if _TRANSLITERATION.search(data):
            self.problems.append(f"a transliteration open to translation: {data.strip()[:50]!r}")
        if _ARABIC_SCRIPT.search(data) and context.language.split("-")[0] not in _READERS_ARABIC_SCRIPT:
            self.problems.append(f"Arabic open to translation: {data.strip()[:50]!r}")

    def _check_element(self, tag: str, values: dict[str, str], outer: _Open) -> None:
        classes = values.get("class", "").split()
        is_untranslated = outer.is_untranslated or values.get("translate") == "no"
        if values.get("lang") == "ar" and (values.get("dir") != "rtl" or not is_untranslated):
            self.problems.append(f'<{tag} lang="ar"> without dir="rtl" translate="no"')
        if values.get("translate") == "no" and "notranslate" not in classes:
            self.problems.append(f'<{tag} translate="no"> without the class notranslate')
        if _QUOTED_AYAH_TRANSLATIONS & set(classes) and values.get("translate") != "no":
            self.problems.append(f"a quoted ayah translation open to translation: <{tag} class={classes}>")


def _problems(page: Path) -> list[str]:
    reader = _Reader()
    reader.feed(page.read_text(encoding="utf-8"))
    language = _folder_language(page)
    wrong_language = [f'<html lang="{reader.page_language}"> on a {language} page'] if reader.page_language != language else []
    return wrong_language + reader.problems


def _folder_language(page: Path) -> str:
    """The language a page is written in: its first folder; the app's own page opens in Bosnian."""
    folder = page.relative_to(PAGES_DIR).parts[0]
    return folder if folder in {language.code for language in LANGUAGES} else "bs"


def _pages() -> Iterator[Path]:
    yield PAGES_DIR / "index.html"
    for language in LANGUAGES:
        yield from sorted((PAGES_DIR / language.code).rglob("index.html"))


@built
def test_no_page_lets_a_browser_translate_the_arabic_the_quoted_ayat_or_a_transliteration():
    problems = [f"{page.relative_to(PAGES_DIR)}: {problem}" for page in _pages() for problem in _problems(page)]
    assert not problems, f"{len(problems)} problems, e.g. {problems[:5]}"


@built
def test_the_not_found_page_is_english_and_safe_to_translate():
    reader = _Reader()
    reader.feed((PAGES_DIR / "404.html").read_text(encoding="utf-8"))
    assert reader.page_language == "en"
    assert not reader.problems


@built
@pytest.mark.parametrize(("code", "has_hint"), [("bs", True), ("en", True), ("tr", False), ("ur", False)])
def test_the_translation_hint_is_on_the_bosnian_and_english_pages_only_and_leads_to_english(code, has_hint):
    verb_page = PAGES_DIR / code / "qala" / "index.html"     # قَالَ, the most frequent verb
    html = verb_page.read_text(encoding="utf-8")
    assert ("data-translate-hint hidden" in html) is has_hint
    assert ("translation.js" in html)        # what the scripts draw later is marked too
    if code == "bs":
        assert 'href="../../en/qala/" hreflang="en" lang="en">Engleska verzija' in html
