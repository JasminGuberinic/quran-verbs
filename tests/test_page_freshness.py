"""The sitemap's <lastmod> follows real content changes, and IndexNow hears of exactly those."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ElementTree

import pytest

from fil import page_version_store
from fil.pages import freshness, indexnow, seo
from fil.pages.freshness import PageVersion
from fil.resources import PAGE_VERSIONS_JSON, PAGES_DIR
from fil.stages import pages

PAGE = '<html><body><h1>قالَ</h1><button data-audio="../../audio/0a1b2c3d4e5f.m4a">▶</button></body></html>'
HOME, QALA, KANA = seo.absolute(""), seo.absolute("bs/qala/"), seo.absolute("bs/kana/")


# ---------- fingerprints: what counts as a change ----------

def test_a_fingerprint_is_a_stable_sha256_of_the_page():
    assert freshness.fingerprint(PAGE) == freshness.fingerprint(PAGE)
    assert freshness.fingerprint(PAGE) == "3f7c61a356ca7a0325b6083ad19d8517"


def test_a_sound_renamed_by_its_content_hash_is_not_a_change():
    re_encoded = PAGE.replace("0a1b2c3d4e5f", "ffeeddccbbaa")
    assert freshness.fingerprint(re_encoded) == freshness.fingerprint(PAGE)


def test_any_change_to_what_the_page_says_is_a_change():
    assert freshness.fingerprint(PAGE.replace("قالَ", "كانَ")) != freshness.fingerprint(PAGE)
    assert freshness.fingerprint(PAGE.replace("audio/0a1b", "audio/x0a1b")) != freshness.fingerprint(PAGE)
    assert freshness.fingerprint(PAGE.replace("data-audio", "data-sound")) != freshness.fingerprint(PAGE)


# ---------- the manifest: golden cases ----------

def test_the_first_build_dates_every_page_today():
    current = freshness.update({}, {QALA: "q1", HOME: "h1"}, "2026-11-06")

    assert current == {HOME: PageVersion("h1", "2026-11-06"), QALA: PageVersion("q1", "2026-11-06")}
    assert list(current) == sorted(current)
    assert freshness.changed({}, current) == (HOME, QALA)


def test_an_unchanged_page_keeps_its_date_a_changed_one_gets_today_and_a_new_one_too():
    recorded = {HOME: PageVersion("h1", "2026-10-01"), QALA: PageVersion("q1", "2026-10-02")}

    current = freshness.update(recorded, {HOME: "h1", QALA: "q2", KANA: "k1"}, "2026-11-06")

    assert current == {HOME: PageVersion("h1", "2026-10-01"), QALA: PageVersion("q2", "2026-11-06"),
                       KANA: PageVersion("k1", "2026-11-06")}
    assert freshness.changed(recorded, current) == (KANA, QALA)


def test_a_page_that_left_the_sitemap_leaves_the_manifest():
    recorded = {HOME: PageVersion("h1", "2026-10-01"), QALA: PageVersion("q1", "2026-10-02")}

    current = freshness.update(recorded, {HOME: "h1"}, "2026-11-06")

    assert current == {HOME: PageVersion("h1", "2026-10-01")}
    assert freshness.changed(recorded, current) == ()


def test_a_rebuild_of_the_same_content_changes_nothing_whatever_the_day():
    recorded = freshness.update({}, {HOME: "h1", QALA: "q1"}, "2026-10-01")

    assert freshness.update(recorded, {HOME: "h1", QALA: "q1"}, "2027-01-01") == recorded
    assert freshness.changed(recorded, recorded) == ()


def test_a_page_changed_twice_in_one_day_is_still_announced_the_second_time():
    recorded = {QALA: PageVersion("q1", "2026-11-06")}

    current = freshness.update(recorded, {QALA: "q2"}, "2026-11-06")

    assert current[QALA].modified == "2026-11-06"
    assert freshness.changed(recorded, current) == (QALA,)


def test_a_date_must_be_a_calendar_day():
    with pytest.raises(ValueError):
        PageVersion("h1", "6.11.2026")


def test_the_manifest_round_trips_sorted(tmp_path):
    manifest = {QALA: PageVersion("q1", "2026-11-06"), HOME: PageVersion("h1", "2026-10-01")}
    path = tmp_path / "page_versions.json"

    page_version_store.save(manifest, path)

    assert page_version_store.load(path) == manifest
    assert list(json.loads(path.read_text(encoding="utf-8"))) == [HOME, QALA]
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2 + len(manifest)     # one page per line
    page_version_store.save({}, path)
    assert page_version_store.load(path) == {}
    assert page_version_store.load(tmp_path / "absent.json") == {}


# ---------- IndexNow ----------

class FakePost:
    """The HttpPost port, recording what would have gone over the network."""

    def __init__(self, *answers: int | OSError) -> None:
        self.answers = list(answers)
        self.sent: list[tuple[str, dict, dict]] = []

    def __call__(self, url: str, body: bytes, headers) -> int:
        self.sent.append((url, json.loads(body), dict(headers)))
        answer = self.answers.pop(0)
        if isinstance(answer, OSError):
            raise answer
        return answer


def test_the_key_is_32_hex_digits_and_its_file_lives_at_the_site_root():
    assert re.fullmatch(r"[0-9a-f]{32}", indexnow.KEY)
    assert indexnow.key_file_name() == f"{indexnow.KEY}.txt"
    assert indexnow.key_location() == f"https://jasminguberinic.github.io/quran-verbs/{indexnow.KEY}.txt"
    assert indexnow.key_file_text() == indexnow.KEY


def test_a_ping_names_host_key_and_key_location_and_lists_the_urls():
    post = FakePost(200)
    lines: list[str] = []

    assert indexnow.ping([HOME, QALA], post, lines.append)

    [(endpoint, body, headers)] = post.sent
    assert endpoint == "https://api.indexnow.org/indexnow"
    assert body == {"host": "jasminguberinic.github.io", "key": indexnow.KEY,
                    "keyLocation": indexnow.key_location(), "urlList": [HOME, QALA]}
    assert headers["Content-Type"].startswith("application/json")
    assert lines == ["IndexNow accepted 2 addresses (HTTP 200)"]


def test_more_than_ten_thousand_urls_go_in_several_requests():
    urls = [seo.absolute(f"bs/verb-{number}/") for number in range(20_001)]

    batches = indexnow.submissions(urls)

    assert [len(batch.urls) for batch in batches] == [10_000, 10_000, 1]
    assert [url for batch in batches for url in batch.urls] == urls
    assert indexnow.submissions([]) == ()


def test_a_failed_or_refused_ping_is_reported_not_raised_and_the_rest_still_go():
    urls = [seo.absolute(f"bs/verb-{number}/") for number in range(20_001)]
    post = FakePost(OSError("network is unreachable"), 422, 202)
    lines: list[str] = []

    assert not indexnow.ping(urls, post, lines.append)

    assert len(post.sent) == 3
    assert lines == ["IndexNow ping failed for 10000 addresses: network is unreachable",
                     "IndexNow refused 10000 addresses: HTTP 422",
                     "IndexNow accepted 1 addresses (HTTP 202)"]


def test_a_deploy_with_nothing_changed_pings_nobody(capsys):
    post = FakePost()

    assert pages.announce((), post)

    assert post.sent == [] and "nothing to announce" in capsys.readouterr().out


def test_the_deploy_announces_through_the_port_it_is_given(capsys):
    post = FakePost(OSError("timed out"))

    assert not pages.announce((QALA,), post)

    assert [body["urlList"] for _, body, _ in post.sent] == [[QALA]]
    assert "IndexNow ping failed" in capsys.readouterr().out


def test_the_deploy_announces_this_builds_changes_and_whatever_the_live_sitemap_dates_differently():
    entries = [seo.SitemapEntry(HOME, "2026-10-01"), seo.SitemapEntry(QALA, "2026-11-05"),
               seo.SitemapEntry(KANA, "2026-11-06")]
    live = {HOME: "2026-10-01", QALA: "2026-10-02", KANA: "2026-11-06"}

    # QALA changed in an earlier, undeployed build; KANA changed again today, on the day it was deployed
    assert indexnow.news(entries, (KANA,), live) == (QALA, KANA)
    assert indexnow.news(entries, (KANA,), None) == (KANA,)
    assert indexnow.news(entries, (), {HOME: "2026-10-01"}) == (QALA, KANA)    # not live yet: new to the engines


def test_the_live_sitemap_is_read_as_address_to_lastmod():
    xml = seo.sitemap([seo.SitemapEntry(HOME, "2026-10-01"), seo.SitemapEntry(QALA, "2026-11-06")])
    assert seo.sitemap_dates(xml) == {HOME: "2026-10-01", QALA: "2026-11-06"}

    undated = xml.replace("<lastmod>2026-10-01</lastmod>", "")
    assert seo.sitemap_dates(undated) == {HOME: "", QALA: "2026-11-06"}


def test_an_unreadable_live_sitemap_leaves_only_this_builds_changes(capsys):
    def offline(url: str) -> str:
        raise OSError("no route to host")

    assert pages.published_dates(offline) is None
    assert pages.published_dates(lambda url: "<not a sitemap") is None
    assert pages.published_dates(lambda url: seo.sitemap([seo.SitemapEntry(HOME, "2026-10-01")])) == {HOME: "2026-10-01"}
    assert "could not be read" in capsys.readouterr().out


# ---------- the built site ----------

built = pytest.mark.skipif(not (PAGES_DIR / "sitemap.xml").is_file(), reason="run `fil pages` first")
_SITEMAP = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


@built
def test_every_sitemap_address_has_the_lastmod_the_manifest_records():
    root = ElementTree.parse(PAGES_DIR / "sitemap.xml").getroot()
    entries = {url.findtext(f"{_SITEMAP}loc"): url.findtext(f"{_SITEMAP}lastmod") for url in root.iter(f"{_SITEMAP}url")}
    manifest = page_version_store.load(PAGE_VERSIONS_JSON)

    assert entries and all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", modified) for modified in entries.values())
    assert entries == {url: version.modified for url, version in manifest.items()}


@built
def test_the_built_pages_match_their_recorded_fingerprints():
    manifest = page_version_store.load(PAGE_VERSIONS_JSON)
    stale = [url for url, version in manifest.items()
             if freshness.fingerprint(pages.page_file(PAGES_DIR, url.removeprefix(seo.SITE_URL))
                                      .read_text(encoding="utf-8")) != version.fingerprint]
    assert stale == []


@built
def test_the_indexnow_key_file_is_published():
    assert (PAGES_DIR / indexnow.key_file_name()).read_text(encoding="utf-8") == indexnow.KEY
