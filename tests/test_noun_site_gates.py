"""Gates of the noun pages: every noun text is voiced, every picture is shown, the site's
navigation is the same everywhere and every link on a noun page leads somewhere.

The unit tests run on small cards; the tests marked "built" read build/pages as `fil pages`
left it and are skipped when it has not been built.
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

from fil import noun_store
from fil.languages import LANGUAGES
from fil.noun_pictures import load_pictures
from fil.nouns.pictures import CREDITED
from fil.pages import render, seo
from fil.resources import PAGES_DIR
from fil.stages.noun_site import UnvoicedNounText, check_voiced, unvoiced_texts

# ---------------------------------------------------------------- the voice gate


def _card(sentence_sound: str | None = "audio/s.m4a") -> dict:
    return {"lemma": "حَقّ", "lemmaSpoken": "audio/l.m4a",
            "table": [{"cells": [{"text": "الْحَقُّ", "audio": "audio/c.m4a"}, {"text": None}]}],
            "explanation": [{"arabic": "الْحَقُّ", "audio": "audio/e.m4a"}],
            "sentences": [{"arabic": "الْحَقُّ وَاضِحٌ", "spoken": sentence_sound}]}


def test_a_fully_voiced_card_passes_the_voice_gate():
    assert unvoiced_texts(_card()) == []
    check_voiced([_card()], {})


def test_a_silent_sentence_stops_the_build():
    with pytest.raises(UnvoicedNounText, match="الْحَقُّ وَاضِحٌ"):
        check_voiced([_card(sentence_sound=None)], {})


def test_a_silent_text_documented_with_a_reason_may_ship():
    check_voiced([_card(sentence_sound=None)], {"الْحَقُّ وَاضِحٌ": "the reader cannot say it yet"})


def test_every_documented_unvoiced_text_gives_a_reason(tmp_path):
    entries = tmp_path / "unvoiced.json"
    entries.write_text(json.dumps({"_about": "x", "الْحَقُّ وَاضِحٌ": ""}, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="reason"):
        noun_store.load_unvoiced(entries)
    assert all(why.strip() for why in noun_store.load_unvoiced().values())


def test_every_shipped_noun_sentence_is_read_alike_by_both_readers():
    """The build gate, without the build: a sentence the checker refuses would ship silent."""
    pytest.importorskip("tts_arabic.text")
    from fil.speech import TtsArabicVoice

    voice, documented = TtsArabicVoice(), noun_store.load_unvoiced()
    refused = [sentence.example.arabic for sentence in noun_store.load_sentences()
               if sentence.example.is_shippable and sentence.example.arabic not in documented
               and not voice.check(sentence.example.arabic).is_faithful]
    assert refused == []


# ---------------------------------------------------------------- the top bar

def _text(code: str = "bs") -> dict:
    return {"page": {"nav": "Glagoli"}, "nounPage": {"nav": "Imenice"}, "language": "Jezik"}


def _language(code: str):
    return next(language for language in LANGUAGES if language.code == code)


def _sections(html: str) -> list[tuple[str, str]]:
    nav = re.search(r'<nav class="sections">(.*?)</nav>', html).group(1)
    return re.findall(r'<a href="([^"]+)"([^>]*)>', nav)


def test_a_verb_page_leads_to_the_verbs_as_its_section_and_to_the_nouns():
    bar = render.top_bar(_text(), "../../", _language("bs"), seo.language_index_path, section=render.VERBS, published={render.NOUNS})
    assert _sections(bar) == [("../../bs/", ' aria-current="true"'), ("../../bs/imenica/", "")]


def test_a_list_page_is_the_current_page_of_its_section():
    bar = render.top_bar(_text(), "../../", _language("en"), seo.language_index_path, section=render.NOUNS, is_section_list=True,
                         published={render.NOUNS})
    assert _sections(bar) == [("../../en/", ""), ("../../en/noun/", ' aria-current="page"')]


@pytest.mark.parametrize("code", [language.code for language in LANGUAGES if language.code not in seo.NOUN_FOLDERS])
def test_a_language_without_noun_pages_has_no_nouns_link(code):
    bar = render.top_bar(_text(), "../", _language(code), seo.language_index_path, section=render.VERBS, published={render.NOUNS})
    assert [path for path, _mark in _sections(bar)] == [f"../{code}/"]


def test_no_nouns_link_before_the_nouns_are_published():
    bar = render.top_bar(_text(), "../", _language("bs"), seo.language_index_path, section=render.VERBS, published=())
    assert len(_sections(bar)) == 1


def test_the_app_hides_the_nouns_link_in_a_language_without_noun_pages():
    app = (Path(render.__file__).parents[1] / "site" / "index.html").read_text(encoding="utf-8")
    sections = re.search(r"function renderSections\(ui\) \{(.*?)\n  \}", app, re.S).group(1)
    section = re.search(r"function renderSection\(link, path, label\) \{(.*?)\n  \}", app, re.S).group(1)
    assert "link.hidden = !path" in section and "paths.en" not in sections
    assert "DATA.nounPages" in sections and "DATA.adjectivePages" in sections and "DATA.nuancePages" in sections
    assert "DATA.particlePages" in sections and 'id="particles-link" hidden' in app
    assert "DATA.pronounPages" in sections and 'id="pronouns-link" hidden' in app
    assert '<a id="verbs-link"' in app and 'id="nouns-link" hidden' in app and 'id="adjectives-link" hidden' in app


# ---------------------------------------------------------------- the built site

built = pytest.mark.skipif(not (PAGES_DIR / "bs" / "imenica" / "index.html").is_file(),
                           reason="build/pages has no noun pages (run `fil pages`)")


class _Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.images: list[str] = []
        self.sections: list[tuple[str, str | None]] = []
        self._in_sections = False

    def handle_starttag(self, tag: str, attrs) -> None:
        found = dict(attrs)
        if tag == "nav" and found.get("class") == "sections":
            self._in_sections = True
        if tag == "a" and found.get("href"):
            self.links.append(found["href"])
            if self._in_sections:
                self.sections.append((found["href"], found.get("aria-current")))
        if tag in ("img", "script") and found.get("src"):
            (self.images if tag == "img" else self.links).append(found["src"])
        if tag == "link" and found.get("href"):
            self.links.append(found["href"])

    def handle_endtag(self, tag: str) -> None:
        if tag == "nav":
            self._in_sections = False


def _parsed(page: Path) -> _Page:
    parser = _Page()
    parser.feed(page.read_text(encoding="utf-8"))
    return parser


def _noun_pages() -> list[Path]:
    """The noun, adjective and nuance pages (all Bosnian and English only)."""
    folders = [*seo.NOUN_FOLDERS.items(), *seo.ADJECTIVE_FOLDERS.items(), *seo.NUANCE_FOLDERS.items()]
    return sorted(path for code, folder in folders for path in (PAGES_DIR / code / folder).rglob("index.html"))


def _verb_pages_sample() -> list[Path]:
    """Each verb list, and the first three verb pages of every language."""
    sample = []
    for language in LANGUAGES:
        folder = PAGES_DIR / language.code
        sections = {*seo.NOUN_FOLDERS.values(), *seo.ADJECTIVE_FOLDERS.values(), *seo.NUANCE_FOLDERS.values()}
        verbs = sorted(page for page in folder.glob("*/index.html") if page.parent.name not in sections)
        sample += [folder / "index.html", *verbs[:3]]
    return sample


def _target(page: Path, href: str) -> Path | None:
    """The file a relative link of `page` opens, or None for a link that leaves the site."""
    parts = urlsplit(href)
    if parts.scheme or parts.netloc or href.startswith(("#", "mailto:")):
        return None
    target = (page.parent / unquote(parts.path)).resolve()
    return target / "index.html" if parts.path.endswith("/") or target.is_dir() else target


@built
def test_every_internal_link_of_the_noun_pages_and_some_verb_pages_resolves():
    broken = [f"{page.relative_to(PAGES_DIR)} → {href}"
              for page in [*_noun_pages(), *_verb_pages_sample()]
              for href in (*_parsed(page).links, *_parsed(page).images)
              for target in [_target(page, href)] if target is not None and not target.is_file()]
    assert broken == []


@built
def test_every_page_has_the_same_top_bar_with_its_section_marked():
    for page in [*_noun_pages(), *_verb_pages_sample()]:
        relative = page.relative_to(PAGES_DIR)
        code, folder = relative.parts[0], relative.parts[1:2]
        is_noun = folder == (seo.NOUN_FOLDERS.get(code),)
        is_adjective = folder == (seo.ADJECTIVE_FOLDERS.get(code),)
        is_nuance = folder == (seo.NUANCE_FOLDERS.get(code),)
        sections = _parsed(page).sections
        expected = 1 + sum(code in folders for folders in (seo.NOUN_FOLDERS, seo.ADJECTIVE_FOLDERS, seo.NUANCE_FOLDERS,
                                                           seo.PARTICLE_FOLDERS, seo.PRONOUN_FOLDERS, seo.EXERCISE_FOLDERS))
        assert len(sections) == expected, relative
        current = [index for index, (_href, mark) in enumerate(sections) if mark]
        assert current == [3 if is_nuance else 2 if is_adjective else 1 if is_noun else 0], relative


@built
def test_every_published_nouns_picture_is_shown_on_its_pages_and_credited():
    pictures = {picture.slug: picture for picture in load_pictures() if picture.has_picture}
    published = {page.parent.name for page in (PAGES_DIR / "en" / "noun").glob("*/index.html")}
    assert published, "no noun pages built"
    credited = {picture.file_name for picture in pictures.values() if picture.source in CREDITED}
    for slug in published & set(pictures):
        for code, folder in seo.NOUN_FOLDERS.items():
            page = PAGES_DIR / code / folder / slug / "index.html"
            html = page.read_text(encoding="utf-8")
            assert f'class="noun-picture" src="../../../pictures/{pictures[slug].file_name}"' in html, page
            assert (PAGES_DIR / "pictures" / pictures[slug].file_name).is_file()
            # A page owes the credit for every licensed picture it shows: its own, or a related noun's (سُوق shows ساق).
            shows_credited = any(f'pictures/{name}"' in html for name in credited)
            assert ("<b>Pictures.</b>" in html) == shows_credited, page
    for code, folder in seo.NOUN_FOLDERS.items():
        listing = (PAGES_DIR / code / folder / "index.html").read_text(encoding="utf-8")
        shown = set(re.findall(r'class="thumb" src="\.\./\.\./pictures/([^"]+)"', listing))
        assert shown == {pictures[slug].file_name for slug in published & set(pictures)}
        assert "<b>Pictures.</b>" in listing


def _credited_files() -> set[str]:
    """Pictures from a licensed set — our own drawings owe no credit."""
    return {picture.file_name for picture in load_pictures() if picture.source in CREDITED}


@built
def test_a_page_carries_the_picture_credit_exactly_when_it_shows_a_licensed_picture():
    credited = _credited_files()
    for page in [*_noun_pages(), *_verb_pages_sample()]:
        html = page.read_text(encoding="utf-8")
        shown = set(re.findall(r'pictures/([^"]+\.svg)"', html))
        assert ("<b>Pictures.</b>" in html) == bool(shown & credited), page
