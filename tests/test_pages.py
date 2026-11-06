"""Tests for the public site's pure parts: page names, addresses, shared audio, the pages."""

import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ElementTree
from pathlib import Path

import pytest

from fil.languages import CODES, LANGUAGES
from fil.pages import deploy, indexing, interface_text, render, seo
from fil.pages.interface_text import fill
from fil.pages.render import EmbeddedAudioOnPublicPage, PublishedVerb
from fil.pages.slugs import assign_slugs, slug_of
from fil.recitation import is_streamed
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

    entries = [seo.SitemapEntry(seo.absolute(path), "2026-11-06") for path in paths]
    root = ElementTree.fromstring(seo.sitemap(entries).encode())
    locations = [element.text for element in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]

    # qala is translated into en + bs only; kana into all; every list has at least half translated
    assert len(locations) == len(set(locations)) == 1 + len(LANGUAGES) * 2 + 2
    assert seo.SITE_URL in locations and seo.absolute("fa/kana/") in locations
    assert seo.absolute("fa/qala/") not in locations and seo.absolute("bs/qala/") in locations


def test_each_sitemap_address_carries_its_own_lastmod():
    entries = [seo.SitemapEntry(seo.absolute(""), "2026-11-01"), seo.SitemapEntry(seo.absolute("bs/qala/"), "2026-11-06")]

    assert seo.sitemap(entries) == (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"<url><loc>{seo.SITE_URL}</loc><lastmod>2026-11-01</lastmod></url>\n"
        f"<url><loc>{seo.SITE_URL}bs/qala/</loc><lastmod>2026-11-06</lastmod></url>\n"
        "</urlset>\n")


def test_a_site_path_is_served_from_its_folder_index_or_as_a_file(tmp_path):
    assert pages.page_file(tmp_path, "") == tmp_path / "index.html"
    assert pages.page_file(tmp_path, "bs/qala/") == tmp_path / "bs" / "qala" / "index.html"
    assert pages.page_file(tmp_path, "llms.txt") == tmp_path / "llms.txt"


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
            "verbDescription": "{0} ({1}): {2}×", "openInApp": "Practice", "allVerbs": "All verbs", "nav": "Verbs", "notFound": "Not found"}
    return {
        "notice": "<b>AI content</b>", "footer": ["<b>Sources.</b>"], "language": "Language", "listen": "Listen",
        "root": "root", "form": "form", "times": "{0}× in the Quran", "inAyat": "in {0} ayat", "ofAll": "{0}% of all",
        "tenses": {"past": "past", "present": "present", "imperative": "command"},
        "pronouns": {pronoun: pronoun for pronoun in render.PRONOUN_ORDER},
        "mainForms": "Main forms", "recited": "as recited", "inQuran": "In the Quran", "participle": "participle",
        "verbalNoun": "verbal noun", "conjugation": "Conjugation", "fullTable": "{0} of {1}", "tableNote": "●",
        "notUsed": "not used", "notUsedNote": "Grey: not used in Arabic.",
        "recitedAyah": "Whole ayah", "noFreeTranslation": "no free translation", "sentences": "Sentences",
        "sentencesNote": "Composed.", "noSentences": "None yet.", "tabs": ["Learn"], "page": page, "nounPage": {"nav": "Nouns"},
        "forms": {"allForms": "Every form ({0})", "formsNote": "Most frequent first.", "firstAyah": "first in",
                  "passive": "passive", "object": "object: {0}",
                  "objects": {pronoun: f"obj-{pronoun}" for pronoun in render.PRONOUN_ORDER},
                  "showAll": "Show all ayat ({0})", "hideAll": "Hide", "showMore": "More", "loading": "Loading",
                  "loadFailed": "Failed",
                  "moods": {"indicative": "indicative", "subjunctive": "subjunctive", "jussive": "jussive"},
                  "links": {"islamBa": "On islam.ba", "wordByWord": "Word by word"}},
    }


def _card() -> dict:
    cell = {"tense": "past", "pronoun": "huwa", "arabic": "قالَ", "plain": "قالَ", "quran": True,
            "spoken": "audio/spoken.m4a", "recited": "audio/recited.m4a", "recitedText": "قالَ"}
    return {
        "rank": 1, "root": "قول", "form": 1, "lemma": "قالَ", "count": 1722, "ayahCount": 1500, "share": 8.04,
        "meaning": {"en": "to say", "bs": "reći"}, "lemmaSpoken": "audio/lemma.m4a", "principal": [cell], "nouns": {},
        "cells": [cell],
        "ayat": [{"ref": "2:30", "tense": "past", "category": {"tense": "past", "pronoun": "huwa", "passive": False, "objects": []},
                  "audio": "https://cdn.islamic.network/quran/audio/64/ar.alafasy/37.mp3",
                  "translation": {"en": {"text": "And when your Lord said <to the angels>", "by": "Sahih International"}},
                  "words": [{"text": "قالَ", "hit": True, "audio": "audio/word.m4a", "gloss": {"en": "said", "bs": "reče"}},
                            {"text": "رَبُّكَ", "hit": False, "audio": None, "gloss": None}]}],
        "forms": [{"arabic": "قَالَ", "count": 412, "first": "2:30", "audio": "audio/form.m4a", "gloss": {"en": "he said", "bs": "rekao je"},
                   "grammar": [{"tense": "past", "pronoun": "huwa", "passive": False, "objects": []}]},
                  {"arabic": "قَالُوهَا", "count": 1, "first": "9:74",
                   "grammar": [{"tense": "past", "pronoun": "hum", "passive": False, "objects": ["hiya"]}]}],
        "ayatFile": "ayat/0001.json", "ayatTranslations": {"en": "ayat/0001.en.json", "ur": "ayat/0001.ur.json"},
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


def test_an_example_verb_not_yet_glossed_shows_its_grammar():
    card = _card()
    card["ayat"][0]["words"][0] = {"text": "قالَ", "hit": True, "audio": "audio/word.m4a", "gloss": None,
                                   "grammar": [{"tense": "past", "pronoun": "hum", "passive": False, "objects": []}]}
    text = _text()
    html = render.verb_page(PublishedVerb(card, "qala"), _language("en"), text)

    label = render.grammar_label(card["ayat"][0]["words"][0]["grammar"], text)
    assert f'= <span class="grammar">{label}</span>' in html


def test_an_example_ayah_is_headed_by_the_form_it_shows():
    text = _text()
    html = render.verb_page(PublishedVerb(_card(), "qala"), _language("en"), text)

    assert f'<span class="tense">{render.grammar_label([_card()["ayat"][0]["category"]], text)}</span>' in html


def test_every_page_plays_through_the_shared_toggling_player_in_its_language():
    html = render.verb_page(PublishedVerb(_card(), "qala"), _language("bs"), {**_text(), "stop": "Zaustavi"})
    untranslated = render.verb_page(PublishedVerb(_card(), "qala"), _language("tr"), _text())

    assert '<script src="../../player.js" data-attribute="data-audio" data-stop-label="Zaustavi" defer></script>' in html
    assert 'data-stop-label="Stop"' in untranslated
    assert '<span class="play-icon notranslate" aria-hidden="true" translate="no">▶</span>' in html


def test_a_page_in_a_language_without_a_meaning_falls_back_to_english_and_says_so():
    html = render.verb_page(PublishedVerb(_card(), "qala"), _language("fa"), _text())

    assert '<html lang="fa" dir="rtl">' in html
    assert '<span class="meaning" lang="en">to say</span>' in html
    assert "no free translation" in html


def test_every_play_button_on_a_page_reaches_the_shared_audio_folder():
    html = render.verb_page(PublishedVerb(_card(), "qala"), _language("en"), _text())
    links = re.findall(r'data-audio="([^"]+)"', html)

    streamed = {link for link in links if is_streamed(link)}
    assert {"../../audio/lemma.m4a", "../../audio/word.m4a", "../../audio/sentence.m4a"} <= set(links)
    assert streamed == {"https://cdn.islamic.network/quran/audio/64/ar.alafasy/37.mp3"}     # the ayah, never a file
    assert all(link.startswith("../../audio/") for link in set(links) - streamed)


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


def test_a_cell_not_used_in_arabic_is_shown_greyed_with_a_note_and_no_sound():
    card = _card()
    unused = {"tense": "imperative", "pronoun": "anta", "arabic": "قُلْ", "plain": "قُلْ", "quran": False,
              "notUsed": True, "spoken": None, "recited": None, "recitedText": None}
    card["cells"] = [*card["cells"], unused]
    html = render.verb_page(PublishedVerb(card, "qala"), _language("en"), _text())

    assert '<td class="not-used"' in html and "<small>not used</small>" in html
    assert "Grey: not used in Arabic." in html
    assert "None" not in html


def test_a_table_without_unused_cells_has_no_unused_note():
    html = render.verb_page(PublishedVerb(_card(), "qala"), _language("en"), _text())
    assert "not-used" not in html and "Grey: not used" not in html


def test_the_language_index_links_each_verb_page():
    html = render.language_index([PublishedVerb(_card(), "qala")], _language("en"), _text())
    assert '<a href="qala/">' in html and f'href="{seo.SITE_URL}en/"' in html


def test_the_404_page_links_absolutely_because_it_is_served_at_any_depth():
    texts = {language.code: _text() for language in LANGUAGES}
    html = render.not_found_page(texts, "/quran-verbs/")
    assert 'href="/quran-verbs/bs/"' in html and 'noindex' in html


_APP_PAGE = Path(pages.__file__).resolve().parents[1] / "site" / "index.html"


def test_no_page_sends_the_browser_asking_the_host_for_a_favicon():
    # A project site's host answers /favicon.ico with 404: an error in the console of every page.
    texts = {language.code: _text() for language in LANGUAGES}
    for html in (render.verb_page(PublishedVerb(_card(), "qala"), _language("en"), _text()),
                 render.not_found_page(texts, "/quran-verbs/"), _APP_PAGE.read_text(encoding="utf-8")):
        assert render.NO_ICON in html.split("</head>")[0]


def test_the_app_top_bar_lets_its_tabs_scroll_instead_of_widening_a_phone_page():
    bar = re.search(r"\.topbar-inner \{([^}]*)\}", _APP_PAGE.read_text(encoding="utf-8")).group(1)
    assert "min-width: 0" in bar and "width: 100%" in bar


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
    card = _translated_card(("en", "bs", "tr", "fr"))
    if missing == "meaning":
        del card["meaning"]["tr"]
    if missing == "sentence":
        del card["sentences"][0]["translation"]["tr"]
    if missing == "gloss":
        del card["ayat"][0]["words"][0]["gloss"]["tr"]

    assert indexing.translated_languages(card) == ("bs", "en", "fr")


def test_an_ayah_gloss_written_only_in_english_and_bosnian_does_not_hold_other_languages_back():
    card = _translated_card(("en", "bs", "tr"))
    card["ayat"][0]["words"].append({"hit": True, "gloss": {"en": "he said", "bs": "rekao je"}})

    assert indexing.translated_languages(card) == ("bs", "en", "tr")


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


# ---------- every form in the Quran, and every ayah on request ----------

def test_a_page_lists_every_form_with_its_count_gloss_and_first_ayah():
    html = render.verb_page(PublishedVerb(_card(), "qala"), _language("bs"), _text())

    assert "Every form (2)" in html
    assert ('<button class="form-play notranslate" type="button" lang="ar" dir="rtl" data-audio="../../audio/form.m4a" translate="no">قَالَ</button>'
            '<small>412×</small>') in html
    assert '<b lang="ar" dir="rtl" translate="no" class="notranslate">قَالُوهَا</b><small>1×</small>' in html   # no recitation: shown, not playable
    assert "rekao je <span class=\"ai\">AI</span>" in html
    assert 'href="https://quran.com/9/74"' in html


def test_a_form_without_a_gloss_shows_its_grammar_and_a_missing_language_falls_back_to_english():
    html = render.verb_page(PublishedVerb(_card(), "qala"), _language("tr"), _text())

    assert '<span class="grammar">past · hum · object: obj-hiya</span>' in html
    assert '<span class="form-gloss" lang="en">he said' in html


def test_a_form_without_our_gloss_shows_its_word_by_word_translation_when_a_source_gives_one():
    card = _card()
    card["forms"][1]["wordTranslation"] = {"en": "they said it"}
    card["forms"][0]["wordTranslation"] = {"bs": "rekao"}

    html = render.verb_page(PublishedVerb(card, "qala"), _language("bs"), _text())

    assert '<span class="form-translation" lang="en">they said it</span>' in html
    assert "rekao je <span class=\"ai\">AI</span>" in html and ">rekao<" not in html   # our own gloss wins


def test_grammar_names_tense_voice_subject_and_objects():
    readings = [{"tense": "past", "pronoun": "huwa", "passive": True, "objects": []},
                {"tense": "present", "pronoun": "anta", "passive": False, "objects": ["hum", "ana"]}]
    assert render.grammar_label(readings, _text()) == "past · passive · huwa / present · anta · object: obj-hum, obj-ana"


def test_the_ayat_are_not_on_the_page_but_one_accessible_button_away():
    html = render.verb_page(PublishedVerb(_card(), "qala"), _language("bs"), _text())

    assert ('<button type="button" class="button quiet" data-all-ayat-toggle aria-expanded="false" '
            'aria-controls="all-ayat-1">Show all ayat (1500)</button>') in html
    assert '<div class="all-ayat-list" id="all-ayat-1" hidden></div>' in html
    assert 'data-ayat="../../ayat/0001.json"' in html and 'src="../../ayat.js"' in html
    assert 'data-translation="../../ayat/0001.en.json"' in html                 # no free Bosnian one
    assert "no free translation" in html.split("data-all-ayat")[1]
    assert 'data-audio-source="https://cdn.islamic.network/quran/audio/64/ar.alafasy/{number}.mp3"' in html
    assert 'data-language="bs"' in html


def test_an_ayah_streams_from_its_source_and_is_never_a_file_of_the_site():
    html = render.verb_page(PublishedVerb(_card(), "qala"), _language("en"), _text())

    assert 'data-audio="https://cdn.islamic.network/quran/audio/64/ar.alafasy/37.mp3"' in html
    assert "audio/ayah" not in html


def test_the_audio_gate_lets_a_streamed_ayah_through_but_not_a_missing_file(tmp_path):
    page = tmp_path / "en" / "qala" / "index.html"
    page.parent.mkdir(parents=True)
    page.write_text('<button data-audio="https://cdn.islamic.network/quran/audio/64/ar.alafasy/37.mp3">', encoding="utf-8")
    pages.check_audio_links(tmp_path, [page])

    page.write_text('<button data-audio="../../audio/absent.m4a">', encoding="utf-8")
    with pytest.raises(pages.BrokenAudioLink):
        pages.check_audio_links(tmp_path, [page])


def test_a_bosnian_reader_is_sent_to_islam_ba_and_everyone_to_the_word_by_word_view():
    bosnian = render.verb_page(PublishedVerb(_card(), "qala"), _language("bs"), _text())
    english = render.verb_page(PublishedVerb(_card(), "qala"), _language("en"), _text())

    assert '<a href="https://islam.ba/kuran/2/30" target="_blank" rel="noopener">On islam.ba ↗</a>' in bosnian
    assert '<a href="https://quranwbw.com/2/30" target="_blank" rel="noopener">Word by word ↗</a>' in bosnian
    assert "https://islam.ba/" not in english and "https://quranwbw.com/2/30" in english
    # a form's row links its first ayah compactly, the label as a tooltip
    assert '<a href="https://quranwbw.com/9/74" target="_blank" rel="noopener" title="Word by word">wbw</a>' in english


def test_a_present_is_labelled_with_its_mood():
    said = {"tense": "present", "pronoun": "huwa", "passive": False, "objects": [], "mood": "indicative"}
    let_say = {**said, "mood": "jussive"}

    assert render.grammar_label([said], _text()) == "present · indicative · huwa"
    assert render.grammar_label([let_say], _text()) == "present · jussive · huwa"


def test_the_ayat_come_in_the_readers_language_when_a_free_translation_exists():
    html = render.verb_page(PublishedVerb(_card(), "qala"), _language("ur"), _text())

    assert 'data-translation="../../ayat/0001.ur.json" data-translation-language="ur" data-translation-dir="rtl"' in html


_NODE_LABELS = """
const ui = require(process.argv[1]), ayat = require(process.argv[2]);
const readings = JSON.parse(process.argv[3]);
const out = { labels: {}, links: {}, compact: {} };
for (const code of Object.keys(ui)) {
  out.labels[code] = ayat.grammarLabel(readings, ui[code]);
  out.links[code] = ayat.ayahLinksHtml("2:255", code, ui[code].forms.links);
  out.compact[code] = ayat.ayahLinksHtml("9:74", code, ui[code].forms.links, true);
}
out.audio = ayat.ayahAudioUrl(process.argv[4], { ref: "2:255", number: 262 });
process.stdout.write(JSON.stringify(out));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_the_app_and_the_pages_label_grammar_link_and_stream_audio_alike():
    from fil.recitation import AYAH_STREAM, ayah_stream
    readings = [{"tense": "past", "pronoun": "hum", "passive": True, "objects": ["huwa", "nahnu"]},
                {"tense": "present", "pronoun": "antum", "passive": False, "objects": [], "mood": "jussive"},
                {"tense": "imperative", "pronoun": "antum", "passive": False, "objects": []}]
    result = subprocess.run(["node", "-e", _NODE_LABELS, str(interface_text.UI_SCRIPT),
                             str(interface_text.UI_SCRIPT.parent / "ayat.js"), json.dumps(readings), AYAH_STREAM],
                            capture_output=True, text=True, check=True)
    from_javascript = json.loads(result.stdout)
    texts = interface_text.load()

    assert from_javascript["audio"] == ayah_stream(2, 255)
    assert from_javascript["labels"] == {code: render.grammar_label(readings, text) for code, text in texts.items()}
    assert from_javascript["links"] == {code: render.ayah_links_html("2:255", code, text["forms"]["links"])
                                        for code, text in texts.items()}
    assert from_javascript["compact"] == {code: render.ayah_links_html("9:74", code, text["forms"]["links"], compact=True)
                                          for code, text in texts.items()}
    assert texts["en"]["forms"]["objects"]["huwa"] == "him/it"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_every_page_credits_every_source_as_its_terms_ask():
    for code, text in interface_text.load().items():
        footer = " ".join(text["footer"])
        for required in ('<a href="https://corpus.quran.com" rel="noopener">Morphology: Quranic Arabic Corpus (GNU GPL)</a>',
                         'href="https://tanzil.net"', 'href="https://tanzil.net/trans/"',
                         "QuranHive Word-by-Word Audio Dataset — © QuranHive, licensed under ",
                         'href="https://quranhive.com"', 'href="https://creativecommons.org/licenses/by/4.0/"',
                         "Recitation: Mishary Rashid Alafasy, streamed from ", 'href="https://alquran.cloud"',
                         'href="https://github.com/nipponjo/tts_arabic"', "by Nawar Halabi (",
                         'href="https://en.arabicspeechcorpus.com/"'):
            assert required in footer, (code, required)
        assert "everyayah" not in footer and "quran.com." not in footer, code
        assert "mustafa0x" not in footer, code          # the modification notice lives in THIRD_PARTY_NOTICES.md


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_every_active_language_names_the_moods_and_the_links_in_its_own_words():
    texts = interface_text.load()
    for code in CODES:
        forms = texts[code]["forms"]
        assert set(forms["moods"]) == {"indicative", "subjunctive", "jussive"}, code
        assert len(set(forms["moods"].values())) == 3, code
        assert set(forms["links"]) == {"islamBa", "wordByWord"}, code
        if code != "en":
            assert forms["moods"] != texts["en"]["forms"]["moods"], code
            assert forms["links"] != texts["en"]["forms"]["links"], code


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_the_interface_speaks_exactly_the_offered_languages():
    assert set(interface_text.load()) == set(CODES)
