"""The phone's navigation (fil.pages.navigation, site/nav.css, site/nav.js): one thin top bar with a ☰ menu
instead of a wall of section pills, and a pager from each word's page to its neighbours and back to its list."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from fil.languages import LANGUAGES
from fil.pages import interface_text, navigation, render, seo
from fil.stages import site

SITE = Path(render.__file__).resolve().parents[1] / "site"


@pytest.fixture(scope="module")
def texts() -> dict[str, dict]:
    return interface_text.load()


def _language(code: str):
    return next(language for language in LANGUAGES if language.code == code)


def _menu(html: str) -> str:
    return re.search(r'<details class="menu" data-menu>.*?</details>', html, re.S).group(0)


# ---------------------------------------------------------------- the top bar and its menu

def test_the_top_bar_names_the_section_and_holds_the_menu_inside_it(texts):
    bar = render.top_bar(texts["bs"], "../../", _language("bs"), seo.language_index_path, section=render.VERBS,
                         published={render.NOUNS})
    header = re.search(r"<header.*?</header>", bar, re.S).group(0)
    assert 'class="top site-top" data-autohide' in header
    assert '<span class="top-title" aria-hidden="true">Glagoli</span>' in header
    assert '<details class="menu" data-menu>' in header          # the ☰ button sits on the one thin line


def test_the_menu_lists_every_section_and_about_with_the_current_one_marked(texts):
    bar = render.top_bar(texts["bs"], "../../", _language("bs"), seo.language_index_path, section=render.NOUNS,
                         is_section_list=True, published={render.NOUNS, render.ADJECTIVES})
    rows = re.findall(r'<a href="([^"]+)" data-section="(\w+)"([^>]*)>', _menu(bar))
    assert [section for _href, section, _mark in rows] == ["verbs", "nouns", "adjectives", "animations", "pictures", "about"]
    assert [section for _href, section, mark in rows if 'aria-current="page"' in mark] == ["nouns"]
    assert rows[-1][0] == f"../../{seo.about_path('bs')}"


def test_the_menu_button_is_labelled_and_says_menu_then_close_in_the_pages_language(texts):
    menu = _menu(render.top_bar(texts["en"], "../", _language("en"), seo.language_index_path, section=render.VERBS))
    assert '<summary class="menu-button" aria-label="Main menu">' in menu
    assert '<span class="menu-word-open">Menu</span><span class="menu-word-close">Close</span>' in menu
    assert '<svg class="menu-icon"' in menu and "☰" not in menu   # a drawn icon, not a text glyph


def test_the_menu_offers_this_page_in_every_language_it_is_written_in(texts):
    menu = _menu(render.top_bar(texts["tr"], "../../", _language("tr"), lambda code: f"{code}/qala/", section=render.VERBS))
    languages = re.findall(r'<a href="\.\./\.\./(\w+)/qala/" hreflang="\1"[^>]*?( aria-current="page")?>', menu)
    assert [code for code, _mark in languages] == [language.code for language in LANGUAGES]
    assert [code for code, mark in languages if mark] == ["tr"]


def test_a_section_written_in_two_languages_offers_only_those(texts):
    menu = _menu(render.top_bar(texts["bs"], "../../", _language("bs"), seo.noun_index_path, section=render.NOUNS,
                                languages=render.BOSNIAN_AND_ENGLISH, published={render.NOUNS}))
    assert re.findall(r'hreflang="(\w+)"', menu) == ["bs", "en"]


def test_the_translation_hint_has_a_short_line_for_a_phone(texts):
    bar = render.top_bar(texts["bs"], "../", _language("bs"), seo.language_index_path, section=render.VERBS)
    assert '<span class="hint-short">Nije tvoj jezik? Prevedi u pregledniku.</span>' in bar


# ---------------------------------------------------------------- the pager

_VERBS = [navigation.Neighbour("qala", "قالَ"), navigation.Neighbour("kana", "كانَ"), navigation.Neighbour("amana", "آمَنَ")]
_WORDS = navigation.PagerWords("← Prethodni", "Sljedeći →", "Svi glagoli")


def test_a_word_stands_between_its_neighbours_in_the_lists_order():
    place = navigation.neighbours_in(_VERBS, "kana")
    assert (place.position, place.total, place.previous.slug, place.next.slug) == (2, 3, "qala", "amana")


def test_the_first_and_the_last_word_have_no_neighbour_on_the_outside():
    assert navigation.neighbours_in(_VERBS, "qala").previous is None
    assert navigation.neighbours_in(_VERBS, "amana").next is None


def test_a_word_missing_from_its_list_fails_fast():
    with pytest.raises(ValueError, match="not in the list"):
        navigation.neighbours_in(_VERBS, "jaa")


def test_the_pager_leads_to_the_sibling_pages_and_back_to_the_list_with_the_place_in_it():
    html = navigation.pager(navigation.neighbours_in(_VERBS, "kana"), "../../bs/", _WORDS)
    assert '<a class="pager-step" rel="prev" href="../qala/"><span>← Prethodni</span>' in html
    assert '<a class="pager-step" rel="next" href="../amana/"><span>Sljedeći →</span>' in html
    assert 'href="../../bs/"' in html and "Svi glagoli" in html and '<span class="pager-count">2 / 3</span>' in html


def test_the_first_word_keeps_the_list_in_the_middle_with_an_empty_step():
    html = navigation.pager(navigation.neighbours_in(_VERBS, "qala"), "../../bs/", _WORDS)
    assert html.count('class="pager-step is-empty" aria-hidden="true"') == 1 and 'rel="prev"' not in html


def test_only_the_foot_pager_stays_in_reach_on_a_phone():
    top, foot = navigation.pagers(navigation.neighbours_in(_VERBS, "kana"), "../../bs/", _WORDS)
    assert 'class="pager"' in top and 'class="pager is-sticky"' in foot


def test_a_verb_page_carries_the_pager_at_its_top_and_its_foot(texts):
    from tests.test_pages import _card   # the verb card the page tests render
    verb = render.PublishedVerb(_card(), "qala")
    page = render.verb_page(verb, _language("bs"), texts["bs"],
                            neighbours=navigation.neighbours_in([navigation.Neighbour("qala", "قالَ"), *_VERBS[1:]], "qala"))
    assert page.count('class="pager-list"') == 2 and "Svi glagoli" in page and 'href="../kana/"' in page


def test_no_pager_without_a_place_in_a_list(texts):
    from tests.test_pages import _card
    page = render.verb_page(render.PublishedVerb(_card(), "qala"), _language("en"), texts["en"])
    assert 'class="pager' not in page


# ---------------------------------------------------------------- shared by the app and every page

def test_every_static_page_loads_the_shared_navigation(texts):
    from tests.test_pages import _card
    page = render.verb_page(render.PublishedVerb(_card(), "qala"), _language("en"), texts["en"])
    assert f'href="../../{render.NAV_STYLESHEET}"' in page and f'src="../../{render.NAV_SCRIPT}"' in page


def test_the_app_uses_the_same_menu_style_and_script():
    app = (SITE / "index.html").read_text(encoding="utf-8")
    assert '<link rel="stylesheet" href="nav.css">' in app and '<script src="nav.js"></script>' in app
    assert '<header class="topbar site-top" data-autohide>' in app and '<details class="menu" data-menu>' in app
    assert 'class="menu-group menu-sections"' in app and 'class="menu-group menu-languages"' in app
    assert {"nav.js", "nav.css"} <= set(site.APP_FILES)


def test_the_apps_verb_strip_and_its_steps_stay():
    """The owner's favourite: the strip of verbs and the ‹ › steps are kept as they are; the card says its place."""
    app = (SITE / "index.html").read_text(encoding="utf-8")
    assert '<div class="chips" id="chips"></div>' in app and 'data-step="-1"' in app and 'data-step="1"' in app
    assert '<span class="hero-count">${current + 1} / ${VERBS.length}</span>' in app


def test_every_section_row_of_the_menu_has_its_icon():
    css = (SITE / "nav.css").read_text(encoding="utf-8")
    sections = ["verbs", "nouns", "adjectives", "nuances", "particles", "pronouns", "roots", "surahs", "exercises",
                "animations", "pictures", "about"]
    assert all(f'[data-section="{section}"]' in css for section in sections)


def test_the_menu_respects_reduced_motion():
    css = (SITE / "nav.css").read_text(encoding="utf-8")
    reduced = css[css.index("prefers-reduced-motion"):]
    assert ".menu-panel, .menu-backdrop { animation: none; }" in reduced and "transition: none" in reduced
