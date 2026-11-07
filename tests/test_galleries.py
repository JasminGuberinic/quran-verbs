"""The two galleries: every verb animation and every noun picture, in every site language."""

from __future__ import annotations

import re
import shutil

import pytest

from fil.languages import CODES, LANGUAGES
from fil.pages import gallery_render, interface_text, render, seo
from fil.pages.animation_render import OWN_DRAWINGS_CREDIT
from fil.pages.gallery_render import ANIMATION_GALLERY, GalleryItem
from fil.pages.render import PublishedVerb
from fil.resources import PAGES_DIR
from fil.stages import gallery_pages
from fil.stages.gallery_pages import GalleryContent

built = pytest.mark.skipif(not (PAGES_DIR / "index.html").exists(), reason="run `fil pages` first")
_SVG = '<svg class="va va-qala_1" viewBox="0 0 120 72"><path d="M0 0"/></svg>'
_PICTURE_CREDIT = "<b>Pictures.</b> OpenMoji, CC BY-SA 4.0."


@pytest.fixture(scope="module")
def texts() -> dict[str, dict]:
    if shutil.which("node") is None:
        pytest.skip("node is not installed")
    return interface_text.load()


def _language(code: str):
    return next(language for language in LANGUAGES if language.code == code)


def _verb(rank: int = 1, slug: str = "qala", meaning: dict | None = None) -> PublishedVerb:
    return PublishedVerb({"rank": rank, "root": "قول", "form": 1, "lemma": "قالَ", "lemmaSpoken": "audio/lemma.m4a",
                          "meaning": meaning or {"en": "to say", "bs": "reći"}}, slug)


def _noun(slug: str = "ard", picture: str | None = "pictures/ard.svg") -> dict:
    return {"slug": slug, "lemma": "أَرْض", "key": "أَرْض|أرض", "meaning": {"en": "earth", "bs": "zemlja"},
            "lemmaSpoken": "audio/ard.m4a", "picture": picture}


def _verb_gallery(*verbs: PublishedVerb) -> list[GalleryItem]:
    return gallery_render.verb_items(verbs or (_verb(),), lambda card: _SVG if card["rank"] == 1 else "")


# ---------- the cards ----------

def test_only_verbs_with_an_animation_are_shown_most_frequent_first():
    items = _verb_gallery(_verb(2, "dakhala"), _verb(1, "qala"))
    assert [item.page_path("en") for item in items] == ["en/qala/"]
    assert items[0].figure == _SVG and items[0].sound == "audio/lemma.m4a"


def test_only_nouns_with_a_picture_are_shown_and_link_their_page_or_the_english_one():
    items = gallery_render.noun_items([_noun(), _noun("ism", picture=None)])
    assert len(items) == 1
    assert items[0].page_path("bs") == "bs/imenica/ard/"
    assert items[0].page_path("tr") == "en/noun/ard/"      # the nouns are written in Bosnian and English only


def test_a_card_is_one_accessible_button_that_plays_the_hero_clip(texts):
    html = gallery_render.gallery_page(ANIMATION_GALLERY, _verb_gallery(), _language("en"), texts["en"])
    button = re.search(r'<button class="gallery-figure"[^>]*>', html).group(0)
    assert 'type="button"' in button and 'data-audio="../../audio/lemma.m4a"' in button
    assert 'aria-label="Listen: قالَ – to say"' in button and 'data-gallery="animations"' in button
    assert f'<span class="gallery-drawing" aria-hidden="true">{_SVG}</span></button>' in html
    assert 'lang="ar" dir="rtl" translate="no">قالَ</span><span class="meaning">to say</span>' in html
    assert '<a class="gallery-link" href="../../en/qala/">Open the page →</a>' in html


def test_a_card_falls_back_to_the_english_meaning_and_says_so(texts):
    html = gallery_render.gallery_page(ANIMATION_GALLERY, _verb_gallery(), _language("tr"), texts["tr"])
    assert '<span class="meaning" lang="en">to say</span>' in html
    assert 'href="../../tr/qala/"' in html


def test_the_animation_page_loops_with_the_replay_script_and_credits_our_drawings(texts):
    html = gallery_render.gallery_page(ANIMATION_GALLERY, _verb_gallery(), _language("bs"), texts["bs"])
    assert html.index('src="../../animation.js"') < html.index('src="../../gallery.js"')     # gallery.js replays through it
    assert OWN_DRAWINGS_CREDIT in html and "<h1>Animacije glagola</h1>" in html
    assert 'href="../../bs/noun-pictures/"' in html                                           # the other gallery


def test_the_picture_page_shows_the_pictures_and_keeps_their_licence_credit(texts):
    items = gallery_render.noun_items([_noun()])
    html = gallery_render.gallery_page(gallery_render.picture_gallery(_PICTURE_CREDIT), items, _language("en"), texts["en"])
    assert '<img src="../../pictures/ard.svg"' in html and 'data-audio="../../audio/ard.m4a"' in html
    assert _PICTURE_CREDIT in html and OWN_DRAWINGS_CREDIT not in html
    assert "animation.js" not in html and 'src="../../gallery.js"' in html
    assert 'href="../../en/animations/"' in html and 'href="../../en/noun/ard/"' in html


# ---------- indexing ----------

def test_a_gallery_is_indexed_only_where_every_caption_is_translated():
    items = _verb_gallery(_verb(meaning={"en": "to say", "bs": "reći", "tr": "demek"}))
    assert gallery_render.indexed_languages(items) == tuple(code for code in CODES if code in {"bs", "en", "tr"})
    nouns = gallery_render.noun_items([_noun()])
    assert set(gallery_render.indexed_languages(nouns)) == {"bs", "en"}
    assert gallery_render.page_paths(ANIMATION_GALLERY, []) == []


def test_an_untranslated_gallery_says_noindex_and_names_no_alternates(texts):
    items = _verb_gallery()
    tr = gallery_render.gallery_page(ANIMATION_GALLERY, items, _language("tr"), texts["tr"])
    assert 'content="noindex, follow"' in tr and 'rel="alternate"' not in tr
    bs = gallery_render.gallery_page(ANIMATION_GALLERY, items, _language("bs"), texts["bs"])
    assert "noindex" not in bs
    assert f'hreflang="en" href="{seo.absolute("en/animations/")}"' in bs
    assert f'<link rel="canonical" href="{seo.absolute("bs/animations/")}">' in bs


def test_both_galleries_are_written_in_every_language_and_listed_where_indexed(texts, tmp_path):
    galleries = (GalleryContent(ANIMATION_GALLERY, tuple(_verb_gallery())),
                 GalleryContent(gallery_render.picture_gallery(_PICTURE_CREDIT), tuple(gallery_render.noun_items([_noun()]))))
    written = gallery_pages.write(tmp_path, galleries, texts)
    assert len(written) == 2 * len(CODES)
    assert all((tmp_path / code / folder / "index.html").is_file() for code in CODES
               for folder in ("animations", "noun-pictures"))
    assert set(gallery_pages.page_paths(galleries)) == {"bs/animations/", "en/animations/",
                                                       "bs/noun-pictures/", "en/noun-pictures/"}


# ---------- the links to them ----------

def test_every_language_names_both_galleries_and_titles_their_pages(texts):
    for code in CODES:
        nav, words = texts[code]["aboutNav"], texts[code]["galleryPage"]
        assert nav["animations"] and nav["pictures"], code
        for key in ("animationsTitle", "animationsIntro", "picturesTitle", "picturesIntro", "openPage"):
            assert words[key], (code, key)
        if code != "en":
            assert words["animationsIntro"] != texts["en"]["galleryPage"]["animationsIntro"], code


def test_the_footer_of_every_page_links_both_galleries(texts):
    page = render.footer_links("bs", "../../", texts["bs"]["aboutNav"])
    assert '<a href="../../bs/animations/">Animacije</a>' in page
    assert '<a href="../../bs/noun-pictures/">Slike imenica</a>' in page
    not_found = render.not_found_page(texts, "/quran-verbs/")
    assert 'href="/quran-verbs/en/animations/"' in not_found and 'href="/quran-verbs/en/noun-pictures/"' in not_found


# ---------- the built site ----------

@built
def test_the_built_galleries_show_every_animation_and_play_only_real_clips():
    from fil.animations.library import load_animations
    english = (PAGES_DIR / "en" / "animations" / "index.html").read_text(encoding="utf-8")
    shown = english.count('class="gallery-card"')
    assert 0 < shown <= len(load_animations())
    for link in re.findall(r'data-audio="([^"]+)"', english):
        assert (PAGES_DIR / "en" / "animations" / link).resolve().is_file(), link
    pictures = (PAGES_DIR / "en" / "noun-pictures" / "index.html").read_text(encoding="utf-8")
    assert pictures.count('class="gallery-card"') > 0
    for source in re.findall(r'<img src="([^"]+)"', pictures):
        assert (PAGES_DIR / "en" / "noun-pictures" / source).resolve().is_file(), source
    assert (PAGES_DIR / gallery_render.GALLERY_SCRIPT).is_file()
