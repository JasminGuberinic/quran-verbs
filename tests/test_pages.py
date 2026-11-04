"""Tests for the public site's pure parts: page names, addresses, shared audio, the pages."""

import re
import xml.etree.ElementTree as ElementTree
from pathlib import Path

import pytest

from fil.languages import CODES, LANGUAGES
from fil.pages import deploy, indexing, render, seo
from fil.pages.interface_text import fill
from fil.pages.render import EmbeddedAudioOnPublicPage, PublishedVerb
from fil.pages.slugs import assign_slugs, slug_of
from fil.site_audio import PublishedAudio, published_name
from fil.stages import pages

# ---------- slugs ----------

@pytest.mark.parametrize(("lemma", "slug"), [
    ("قالَ", "qala"), ("كانَ", "kana"), ("آمَنَ", "amana"), ("كَذَّبَ", "kadhdhaba"),
    ("اتَّقَى", "ittaqa"), ("خَلَقَ", "khalaqa"), ("تَوَلَّى", "tawalla"), ("لَيْسَ", "laysa"),
])
def test_a_slug_is_a_plain_ascii_reading_of_the_lemma(lemma, slug):
    assert slug_of(lemma) == slug


def test_slugs_are_url_safe_ascii():
    for lemma in ("قالَ", "عَلِمَ", "أَتَى", "سَأَلَ", "ءَ"):
        assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug_of(lemma))


def test_verbs_that_read_alike_get_distinct_slugs_and_the_more_frequent_keeps_the_plain_one():
    assert assign_slugs(["آتَى", "أَتَى", "اتَى"]) == ["ata", "ata-2", "ita"]
    assert assign_slugs(["آتَى", "أَتَى", "آتَى"]) == ["ata", "ata-2", "ata-3"]


def test_slugs_are_stable_when_verbs_are_studied_later():
    catalogue = ["قالَ", "آتَى", "أَتَى", "كانَ"]
    cards_now = [{"rank": 3, "lemma": "أَتَى"}]
    cards_later = [{"rank": 1, "lemma": "قالَ"}, {"rank": 2, "lemma": "آتَى"}, {"rank": 3, "lemma": "أَتَى"}]

    before = {verb.card["rank"]: verb.slug for verb in pages.published_verbs(cards_now, catalogue)}
    after = {verb.card["rank"]: verb.slug for verb in pages.published_verbs(cards_later, catalogue)}

    assert before[3] == after[3] == "ata-2"


# ---------- addresses, alternates, sitemap ----------

def test_a_page_lists_its_indexed_languages_and_an_x_default():
    alternates = seo.verb_alternates("qala", CODES)

    assert [item.hreflang for item in alternates] == [*CODES, "x-default"]
    assert alternates[-1].url == seo.absolute("en/qala/")
    assert all(item.url.startswith(seo.SITE_URL) for item in alternates)
    assert [item.hreflang for item in seo.verb_alternates("qala", ("en", "bs"))] == ["bs", "en", "x-default"]


def test_alternates_refuse_a_language_the_site_does_not_have():
    with pytest.raises(ValueError):
        seo.index_alternates(("en", "xx"))


def test_relative_paths_find_the_root_from_any_depth():
    assert seo.to_root("") == ""
    assert seo.to_root("bs/") == "../"
    assert seo.to_root("bs/qala/") == "../../"


def test_the_sitemap_lists_every_indexable_page_once_as_valid_xml():
    verbs = [PublishedVerb(_card(), "qala"), PublishedVerb(_translated_card(CODES), "kana")]
    paths = pages.page_paths(verbs)

    root = ElementTree.fromstring(seo.sitemap(paths).encode())
    locations = [element.text for element in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]

    # qala is translated into en + bs only; kana into all; every list has at least half translated
    assert len(locations) == len(set(locations)) == 1 + len(LANGUAGES) * 2 + 2
    assert seo.SITE_URL in locations and seo.absolute("fa/kana/") in locations
    assert seo.absolute("fa/qala/") not in locations and seo.absolute("bs/qala/") in locations


def test_robots_points_to_the_sitemap():
    assert f"Sitemap: {seo.SITE_URL}sitemap.xml" in seo.robots()


# ---------- shared audio ----------

def test_the_same_sound_is_stored_once_whatever_its_source(tmp_path):
    first, second, other = tmp_path / "a.m4a", tmp_path / "b.m4a", tmp_path / "c.m4a"
    first.write_bytes(b"one sound")
    second.write_bytes(b"one sound")
    other.write_bytes(b"another sound")
    site = tmp_path / "site"
    sink = PublishedAudio(site)

    references = [sink.reference(first), sink.reference(second), sink.reference(other), sink.reference(first)]

    assert references[0] == references[1] == references[3] != references[2]
    assert references[0] == published_name(b"one sound")
    assert sorted(path.name for path in (site / "audio").iterdir()) == sorted(
        Path(reference).name for reference in set(references))


def test_a_card_with_embedded_sound_cannot_reach_the_public_site():
    with pytest.raises(EmbeddedAudioOnPublicPage):
        render.audio_link("data:audio/mp4;base64,AAAA", "../../")


def test_every_sound_in_a_card_is_found():
    card = {"lemmaSpoken": "audio/a.m4a", "cells": [{"spoken": "audio/b.m4a", "recited": None}],
            "ayat": [{"words": [{"audio": "audio/c.m4a", "text": "x"}]}], "lemma": "قالَ"}
    assert sorted(pages.sound_references(card)) == ["audio/a.m4a", "audio/b.m4a", "audio/c.m4a"]


# ---------- the pages themselves ----------

def _text() -> dict:
    page = {"indexTitle": "Verbs of the Quran", "indexIntro": "Every verb.", "verbTitle": "{0} – {1} · verb",
            "verbDescription": "{0} ({1}): {2}×", "openInApp": "Practice", "allVerbs": "All verbs", "notFound": "Not found"}
    return {
        "notice": "<b>AI content</b>", "footer": ["<b>Sources.</b>"], "language": "Language", "listen": "Listen",
        "root": "root", "form": "form", "times": "{0}× in the Quran", "inAyat": "in {0} ayat", "ofAll": "{0}% of all",
        "tenses": {"past": "past", "present": "present", "imperative": "command"},
        "pronouns": {pronoun: pronoun for pronoun in render.PRONOUN_ORDER},
        "mainForms": "Main forms", "recited": "as recited", "inQuran": "In the Quran", "participle": "participle",
        "verbalNoun": "verbal noun", "conjugation": "Conjugation", "fullTable": "{0} of {1}", "tableNote": "●",
        "recitedAyah": "Whole ayah", "noFreeTranslation": "no free translation", "sentences": "Sentences",
        "sentencesNote": "Composed.", "noSentences": "None yet.", "tabs": ["Learn"], "page": page,
    }


def _card() -> dict:
    cell = {"tense": "past", "pronoun": "huwa", "arabic": "قالَ", "plain": "قالَ", "quran": True,
            "spoken": "audio/spoken.m4a", "recited": "audio/recited.m4a", "recitedText": "قالَ"}
    return {
        "rank": 1, "root": "قول", "form": 1, "lemma": "قالَ", "count": 1722, "ayahCount": 1500, "share": 8.04,
        "meaning": {"en": "to say", "bs": "reći"}, "lemmaSpoken": "audio/lemma.m4a", "principal": [cell], "nouns": {},
        "cells": [cell],
        "ayat": [{"ref": "2:30", "tense": "past", "audio": "audio/ayah.m4a",
                  "translation": {"en": {"text": "And when your Lord said <to the angels>", "by": "Sahih International"}},
                  "words": [{"text": "قالَ", "hit": True, "audio": "audio/word.m4a", "gloss": {"en": "said", "bs": "reče"}},
                            {"text": "رَبُّكَ", "hit": False, "audio": None, "gloss": None}]}],
        "sentences": [{"arabic": "قالَ", "spoken": "audio/sentence.m4a", "translation": {"en": "He said.", "bs": "Rekao je."},
                       "words": [{"arabic": "قالَ", "target": True, "translation": {"en": "said"}}]}],
    }


def _language(code: str):
    return next(language for language in LANGUAGES if language.code == code)


def test_a_verb_page_is_complete_readable_html_in_its_language():
    html = render.verb_page(PublishedVerb(_card(), "qala"), _language("bs"), _text())

    assert '<html lang="bs" dir="ltr">' in html
    assert "<title>قالَ – reći · verb</title>" in html
    assert f'<link rel="canonical" href="{seo.SITE_URL}bs/qala/">' in html
    assert html.count('rel="alternate" hreflang=') == 3          # bs, en, x-default: the translated ones
    assert "Sahih International" in html and "&lt;to the angels&gt;" in html   # content is escaped
    assert "<b>AI content</b>" in html                                         # the notice is shown
    assert "Rekao je." in html and "reče" in html
    assert 'href="../../index.html?lang=bs#verb-1"' in html
    assert 'application/ld+json' in html and 'og:image' in html


def test_a_page_in_a_language_without_a_meaning_falls_back_to_english_and_says_so():
    html = render.verb_page(PublishedVerb(_card(), "qala"), _language("fa"), _text())

    assert '<html lang="fa" dir="rtl">' in html
    assert '<span class="meaning" lang="en">to say</span>' in html
    assert "no free translation" in html


def test_every_play_button_on_a_page_reaches_the_shared_audio_folder():
    html = render.verb_page(PublishedVerb(_card(), "qala"), _language("en"), _text())
    links = re.findall(r'data-audio="([^"]+)"', html)

    assert {"../../audio/lemma.m4a", "../../audio/word.m4a", "../../audio/ayah.m4a", "../../audio/sentence.m4a"} <= set(links)
    assert all(link.startswith("../../audio/") for link in links)


def test_the_audio_gate_fails_on_a_missing_file(tmp_path):
    page = tmp_path / "en" / "qala" / "index.html"
    page.parent.mkdir(parents=True)
    page.write_text(render.verb_page(PublishedVerb(_card(), "qala"), _language("en"), _text()), encoding="utf-8")

    with pytest.raises(pages.BrokenAudioLink):
        pages.check_audio_links(tmp_path, [page])

    (tmp_path / "audio").mkdir()
    for name in set(re.findall(r"audio/([\w.]+)", page.read_text(encoding="utf-8"))):
        (tmp_path / "audio" / name).write_bytes(b"sound")
    pages.check_audio_links(tmp_path, [page])


def test_the_language_index_links_each_verb_page():
    html = render.language_index([PublishedVerb(_card(), "qala")], _language("en"), _text())
    assert '<a href="qala/">' in html and f'href="{seo.SITE_URL}en/"' in html


def test_the_404_page_links_absolutely_because_it_is_served_at_any_depth():
    texts = {language.code: _text() for language in LANGUAGES}
    html = render.not_found_page(texts, "/quran-verbs/")
    assert 'href="/quran-verbs/bs/"' in html and 'noindex' in html


def test_templates_fill_their_numbered_holes():
    assert fill("{0} of {1}", 3, 5) == "3 of 5"


def test_structured_data_cannot_end_its_script_early():
    data = seo.verb_structured_data(title="</script>", description="d", language="en", path="en/x/",
                                    lemma="x", meaning="m", index_title="t")
    assert "</script>" not in data


# ---------- deployment ----------

def test_deployment_commits_the_build_alone_and_force_pushes_the_orphan_branch(tmp_path):
    commands = deploy.publish_commands(tmp_path / "pages", tmp_path / "git", "https://example/repo.git",
                                       deploy.Identity("Name", "name@example.com"), "Publish")

    assert all(f"--work-tree={tmp_path / 'pages'}" in command for command in commands)
    assert "--initial-branch=gh-pages" in commands[0]
    assert commands[-1][-3:] == ["--quiet", "https://example/repo.git", "gh-pages:gh-pages"]
    assert "--force" in commands[-1]


def test_published_slugs_of_the_whole_catalogue_are_unique_and_never_change():
    from fil import service
    slugs = assign_slugs(verb.lemma for verb in service.list_verbs())

    assert len(slugs) == len(set(slugs))
    # Published addresses: changing one breaks links people have shared.
    assert slugs[:12] == ["qala", "kana", "amana", "alima", "jaala", "kafara",
                          "jaa", "amila", "ata", "raa", "ata-2", "shaa"]


# ---------- what search engines may index ----------

def _translated_card(languages) -> dict:
    """The test card with its meaning, sentence and ayah gloss in every one of `languages`."""
    card = _card()
    card["meaning"] = {language: f"meaning-{language}" for language in languages}
    card["sentences"][0]["translation"] = {language: f"sentence-{language}" for language in languages}
    card["ayat"][0]["words"][0]["gloss"] = {language: f"gloss-{language}" for language in languages}
    return card


@pytest.mark.parametrize("missing", ["meaning", "sentence", "gloss"])
def test_a_page_is_translated_only_when_meaning_sentences_and_ayah_glosses_all_are(missing):
    card = _translated_card(("en", "bs", "tr"))
    if missing == "meaning":
        del card["meaning"]["tr"]
    if missing == "sentence":
        del card["sentences"][0]["translation"]["tr"]
    if missing == "gloss":
        del card["ayat"][0]["words"][0]["gloss"]["tr"]

    assert indexing.translated_languages(card) == ("bs", "en")


def test_english_counts_as_translated_for_english_alone():
    card = _translated_card(("en",))
    assert indexing.translated_languages(card) == ("en",)
    assert not indexing.is_translated(card, "bs")


def test_an_untranslated_page_is_built_and_linked_but_kept_out_of_search():
    html = render.verb_page(PublishedVerb(_card(), "qala"), _language("fa"), _text())

    assert '<meta name="robots" content="noindex, follow">' in html
    assert 'rel="alternate"' not in html
    assert 'href="../../bs/qala/"' in html                                  # visitors can still switch


def test_a_translated_page_names_only_its_translated_siblings():
    html = render.verb_page(PublishedVerb(_card(), "qala"), _language("bs"), _text())

    assert "noindex" not in html
    assert re.findall(r'hreflang="([\w-]+)" href="https', html) == ["bs", "en", "x-default"]


def test_a_list_is_indexed_once_at_least_half_its_verb_pages_are_translated():
    half = [_card(), _translated_card(CODES)]
    less = [_card(), _card(), _translated_card(CODES)]

    assert indexing.is_list_indexable(half, "fa")
    assert not indexing.is_list_indexable(less, "fa")
    assert indexing.indexable_lists(less) == ("bs", "en")


def test_a_list_below_the_threshold_still_lists_every_verb_but_says_noindex():
    verbs = [PublishedVerb(_card(), "qala"), PublishedVerb(_card(), "kana"), PublishedVerb(_translated_card(CODES), "ata")]
    html = render.language_index(verbs, _language("fa"), _text())

    assert 'content="noindex, follow"' in html
    assert all(f'<a href="{slug}/">' in html for slug in ("qala", "kana", "ata"))
    assert "noindex" not in render.language_index(verbs, _language("bs"), _text())
