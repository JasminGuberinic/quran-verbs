"""Browser page translation (Chrome, Edge, Safari) must never touch the Arabic, the ayah
translations we quote, or the transliterations (fil.pages.untranslated, site/translation.js)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from fil.pages import untranslated
from fil.pages.untranslated import protect, untranslatable_runs

_TRANSLATION_SCRIPT = Path(__file__).resolve().parents[1] / "src" / "fil" / "site" / "translation.js"
_ARABIC_SPAN = '<span lang="ar" dir="rtl" translate="no" class="notranslate">'
_TRANSLITERATION_SPAN = '<span lang="ar-Latn" translate="no" class="notranslate">'


def test_an_element_in_arabic_is_left_untranslated_and_reads_right_to_left():
    assert protect('<span class="ar" lang="ar">قَالَ</span>', "en") == (
        '<span class="ar notranslate" lang="ar" dir="rtl" translate="no">قَالَ</span>')
    assert protect("<b lang='ar' dir='rtl'>قَالَ</b>", "bs") == (
        "<b lang='ar' dir='rtl' translate=\"no\" class=\"notranslate\">قَالَ</b>")


def test_what_a_renderer_marks_untranslated_also_carries_the_class_older_google_translate_reads():
    assert protect('<figcaption class="translation" lang="en" translate="no">Say: He is Allah</figcaption>', "bs") == (
        '<figcaption class="translation notranslate" lang="en" translate="no">Say: He is Allah</figcaption>')


def test_arabic_inside_translatable_text_is_wrapped_and_the_text_around_it_is_not():
    assert protect("<p>čestica iz porodice إِنَّ · korpus: 9×</p>", "bs") == (
        f"<p>čestica iz porodice {_ARABIC_SPAN}إِنَّ</span> · korpus: 9×</p>")
    # several Arabic words are one run
    assert protect("<p>komparativ (أَفْعَلُ مِنْ):</p>", "bs") == f"<p>komparativ ({_ARABIC_SPAN}أَفْعَلُ مِنْ</span>):</p>"


def test_transliterations_and_the_name_of_the_site_are_wrapped_as_romanized_arabic():
    assert protect('<a class="brand" href="./">Fiʿl</a>', "en") == (
        f'<a class="brand" href="./">{_TRANSLITERATION_SPAN}Fiʿl</span></a>')
    assert protect("<p>al-Rāghib al-Iṣfahānī, Mufradāt — the iḍāfa</p>", "en") == (
        f"<p>{_TRANSLITERATION_SPAN}al-Rāghib al-Iṣfahānī</span>, {_TRANSLITERATION_SPAN}Mufradāt</span>"
        f" — the {_TRANSLITERATION_SPAN}iḍāfa</span></p>")


@pytest.mark.parametrize("words", ["Prevedi stranicu u pregledniku", "Kur'an'ın en sık geçen fiili", "à côté de l'âme",
                                   "Sadržaj je generisala umjetna inteligencija", "kata kerja yang paling sering"])
def test_the_words_of_our_languages_are_never_taken_for_a_transliteration(words):
    assert protect(f"<p>{words}</p>", "bs") == f"<p>{words}</p>"


def test_on_a_persian_or_urdu_page_arabic_script_is_the_readers_own_unless_it_says_it_is_arabic():
    page = '<p>معنی (يَنْبَغِي) <b lang="ar">قَالَ</b> iḍāfa</p>'
    assert protect(page, "fa") == (f'<p>معنی (يَنْبَغِي) <b lang="ar" dir="rtl" translate="no" class="notranslate">قَالَ</b> '
                                   f'{_TRANSLITERATION_SPAN}iḍāfa</span></p>')
    # and a language's own name in its own script, on any page, is the renderer's to mark
    assert protect('<a lang="ur">اردو</a>', "en") == '<a lang="ur">اردو</a>'


def test_nothing_inside_an_untranslated_element_is_wrapped_again():
    once = protect('<p>riječ <span lang="ar">قَالَ</span> i إِنَّ</p><p translate="no">Fiʿl قَالَ</p>', "bs")
    assert protect(once, "bs") == once
    assert once.count("<span") == 2


def test_scripts_comments_and_attributes_are_left_as_they_are():
    page = ('<!-- إِنَّ --><script>const word = "<b>إِنَّ</b>";</script>'
            '<div data-text=\'{"a":"إِنَّ"}\' title="Fiʿl"><img src="x.svg" alt=""><svg><path d="M0"/></svg>riječ</div>')
    assert protect(page, "bs") == page


def test_an_element_left_open_by_html_rules_does_not_carry_its_context_past_its_parent():
    page = '<ul lang="ar"><li>قَالَ</ul><p>إِنَّ</p>'
    assert protect(page, "bs").endswith(f"<p>{_ARABIC_SPAN}إِنَّ</span></p>")


def test_markup_the_pass_cannot_follow_fails_the_build():
    with pytest.raises(untranslated.UnreadableMarkup):
        protect("<script>never closed", "bs")


_SAMPLES = ["čestica iz porodice إِنَّ · korpus", "Fiʿl · al-Rāghib al-Iṣfahānī", "komparativ (أَفْعَلُ مِنْ): ‘…-er than’",
            "معنی (يَنْبَغِي) iḍāfa", "ʿAbbās, Ibn ʿAbbās and Qurʾān", "plain words, nothing to keep", "قَالَ إِنَّ‌هُ"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
@pytest.mark.parametrize("is_arabic_script", [False, True])
def test_the_browser_finds_the_same_runs_as_the_build(is_arabic_script):
    """site/translation.js marks what the scripts draw; it must agree with the build character for character."""
    script = (f"const T = require({json.dumps(str(_TRANSLATION_SCRIPT))});"
              f"const samples = {json.dumps(_SAMPLES, ensure_ascii=False)};"
              f"process.stdout.write(JSON.stringify(samples.map((text) => T.untranslatableRuns(text, {json.dumps(is_arabic_script)}))));")
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    in_browser = json.loads(result.stdout)
    in_build = [[{"kind": run.kind, "text": run.text, "index": run.start} for run in untranslatable_runs(text, is_arabic_script)]
                for text in _SAMPLES]
    assert in_browser == in_build
