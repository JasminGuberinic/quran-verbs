"""The About page with its Privacy section, the footer links to it, and the installable app (PWA)."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from fil.languages import CODES, LANGUAGES
from fil.pages import about_render, about_text, interface_text, pwa, render, seo
from fil.pages.about_text import ABOUT
from fil.pages.render import PublishedVerb
from fil.resources import PAGES_DIR
from fil.stages import about_pages, site

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
SITE_SOURCES = Path(site.__file__).resolve().parents[1] / "site"
built = pytest.mark.skipif(not (PAGES_DIR / "index.html").exists(), reason="run `fil pages` first")


@pytest.fixture(scope="module")
def texts() -> dict[str, dict]:
    if shutil.which("node") is None:
        pytest.skip("node is not installed")
    return interface_text.load()


def _language(code: str):
    return next(language for language in LANGUAGES if language.code == code)


# ---------- the About page ----------

def test_every_site_language_has_its_own_complete_about_text():
    assert set(ABOUT) == set(CODES)
    for code, words in ABOUT.items():
        for field in about_text.AboutText.__dataclass_fields__:
            assert getattr(words, field), (code, field)
        assert len(words.privacy_points) == 4, code
    assert ABOUT["bs"].made != ABOUT["en"].made


def test_the_about_page_says_what_the_owner_asked_and_names_no_person(texts):
    html = about_render.about_page(_language("en"), texts)
    for required in ("Claude Code", "not a religious authority", "not tafsir and not a fatwa", "Tanzil",
                     "No ads, no payments, no registration", about_render.NOTICES_URL, 'id="privacy"',
                     "No cookies, no tracking, no analytics and no account", "localStorage",
                     about_render.GITHUB_PRIVACY_URL, "automatic tests", "AI translations"):
        assert required in html, required
    assert "Jasmin" not in html.replace(about_render.NOTICES_URL, "")
    for name, url in about_render.SOURCES:
        assert f'href="{url}"' in html, name


def test_the_about_page_is_indexed_in_every_language_with_alternates(texts):
    html = about_render.about_page(_language("bs"), texts)
    assert "noindex" not in html
    for code in CODES:
        assert f'hreflang="{code}" href="{seo.absolute(seo.about_path(code))}"' in html
    assert f'<link rel="canonical" href="{seo.absolute("bs/about/")}">' in html


def test_the_about_pages_are_written_and_listed_for_the_sitemap(texts, tmp_path):
    written = about_pages.write(tmp_path, texts)
    assert len(written) == len(CODES)
    assert (tmp_path / "bs" / "about" / "index.html").is_file()
    assert about_pages.page_paths() == [f"{code}/about/" for code in CODES]


def test_the_footer_links_to_about_and_privacy_from_every_kind_of_page(texts):
    card = PublishedVerb(_verb_card(), "qala")
    verb_page = render.verb_page(card, _language("en"), texts["en"])
    assert '<a href="../../en/about/">About</a> · <a href="../../en/about/#privacy">Privacy</a>' in verb_page
    index = render.language_index([card], _language("bs"), texts["bs"])
    assert '<a href="../bs/about/">O stranici</a> · <a href="../bs/about/#privacy">Privatnost</a>' in index
    for html in (verb_page, index):
        assert render._ABOUT_LINKS not in html and "pwa.js" in html and 'rel="manifest"' in html


def test_the_404_page_links_the_about_page_and_the_manifest(texts):
    html = render.not_found_page(texts, "/quran-verbs/")
    assert 'href="/quran-verbs/en/about/"' in html
    assert 'rel="manifest" href="/quran-verbs/manifest.webmanifest"' in html


def _verb_card() -> dict:
    from test_pages import _card
    return _card()


# ---------- the privacy claim ----------

_ALLOWED_HOSTS = {
    "fonts.googleapis.com", "fonts.gstatic.com",          # typefaces, loaded when a page opens
    "cdn.islamic.network",                                # whole-ayah recitation, streamed on play
    "quran.com", "quranwbw.com", "islam.ba",              # outbound links, contacted only on a click
    "www.w3.org",                                         # an SVG namespace name, never requested
}
_TRACKERS = ("google-analytics", "googletagmanager", "gtag(", "document.cookie", "sendBeacon", "plausible", "matomo",
             "facebook", "hotjar", "XMLHttpRequest", "WebSocket")


def _site_sources() -> list[Path]:
    return [path for path in SITE_SOURCES.iterdir() if path.suffix in (".js", ".html", ".css")]


def test_no_script_or_page_of_the_site_tracks_or_contacts_anyone_unlisted():
    for path in _site_sources():
        source = path.read_text(encoding="utf-8")
        for tracker in _TRACKERS:
            assert tracker not in source, (path.name, tracker)
        hosts = set(re.findall(r"https?://([a-zA-Z0-9.-]+)", source))
        assert hosts <= _ALLOWED_HOSTS | _ui_text_hosts(path), (path.name, sorted(hosts - _ALLOWED_HOSTS))


def _ui_text_hosts(path: Path) -> set[str]:
    """ui.js carries the footer's credit links: outbound links to the sources, clicked or never."""
    if path.name != "ui.js":
        return set()
    return set(re.findall(r"https?://([a-zA-Z0-9.-]+)", path.read_text(encoding="utf-8")))


def test_the_privacy_section_names_every_host_a_page_may_contact():
    for code, words in ABOUT.items():
        for host in ("fonts.googleapis.com", "fonts.gstatic.com", "cdn.islamic.network", "quran.com", "quranwbw.com",
                     "islam.ba"):
            assert host in words.third_parties, (code, host)


# ---------- the manifest ----------

def test_the_manifest_starts_at_the_app_home_inside_the_project_scope():
    manifest = json.loads(json.dumps(pwa.manifest()))
    assert manifest["start_url"] == "/quran-verbs/" and manifest["scope"] == "/quran-verbs/"
    assert "about" not in manifest["start_url"]
    assert manifest["display"] == "standalone" and manifest["name"] == "Fiʿl"
    assert {icon["sizes"] for icon in manifest["icons"]} == {"192x192", "512x512"}
    assert {"any", "maskable"} == {icon["purpose"] for icon in manifest["icons"]}
    for icon in manifest["icons"]:
        assert (SITE_SOURCES / icon["src"]).is_file()
    css = (SITE_SOURCES / render.STYLESHEET).read_text(encoding="utf-8")
    assert f"--accent: {manifest['theme_color']}" in css and f"--paper: {manifest['background_color']}" in css


def test_the_service_worker_is_stamped_with_the_build_and_the_shell(tmp_path):
    for name, body in (("index.html", "a"), ("ui.js", "b"), ("pages.css", "c"), ("sitemap.xml", "d"), ("data.json", "{}"),
                       ("404.html", "e")):
        (tmp_path / name).write_text(body, encoding="utf-8")
    shutil.copytree(SITE_SOURCES / pwa.ICONS_FOLDER, tmp_path / pwa.ICONS_FOLDER)
    first = pwa.service_worker(tmp_path)
    assert "__BUILD__" not in first and "__SHELL__" not in first
    assert pwa.build_id(tmp_path) in first and '"index.html"' in first and '"icons/icon-192.png"' in first
    (tmp_path / "ui.js").write_text("changed", encoding="utf-8")
    assert pwa.service_worker(tmp_path) != first          # a changed shell is a new worker, so the old caches go


def test_the_worker_source_keeps_both_placeholders():
    source = (SITE_SOURCES / pwa.SERVICE_WORKER_FILE).read_text(encoding="utf-8")
    assert source.count("__BUILD__") == 1 and source.count("__SHELL__") == 1


# ---------- every built page ----------

@built
def test_every_built_page_links_the_manifest_and_the_about_page():
    proofs = {proof.name for proof in (SITE_SOURCES / "verification").glob("*")}    # a search engine's one-line ownership file
    pages = [path for path in PAGES_DIR.rglob("*.html") if path.name not in proofs]
    assert pages
    missing = []
    for page in pages:
        html = page.read_text(encoding="utf-8")
        if 'rel="manifest"' not in html or "about/" not in html:
            missing.append(str(page.relative_to(PAGES_DIR)))
    assert not missing, f"{len(missing)} pages lack the manifest or the About link, e.g. {missing[:3]}"


@built
def test_the_built_site_holds_the_pwa_files_and_a_valid_manifest():
    manifest = json.loads((PAGES_DIR / pwa.MANIFEST_FILE).read_text(encoding="utf-8"))
    assert manifest["start_url"] == "/quran-verbs/"
    for name in (pwa.SERVICE_WORKER_FILE, pwa.PWA_SCRIPT, pwa.ROUTING_SCRIPT):
        assert (PAGES_DIR / name).is_file()
    assert "__BUILD__" not in (PAGES_DIR / pwa.SERVICE_WORKER_FILE).read_text(encoding="utf-8")
    sitemap = (PAGES_DIR / "sitemap.xml").read_text(encoding="utf-8")
    assert all(seo.absolute(seo.about_path(code)) in sitemap for code in CODES)
