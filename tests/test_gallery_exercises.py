"""The galleries in the top bar, and their own exercises: Animacija → glagol (and Slika → riječ, the pictures')."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from fil.exercises import gate
from fil.exercises.model import ANIMATION, KINDS, PICTURE, Bilingual as B, Option, word_id
from fil.exercises.vocabulary import Word, animation_exercises
from fil.languages import CODES, LANGUAGES
from fil.pages import exercise_render, gallery_render, interface_text, render
from fil.pages.animation_render import OWN_DRAWINGS_CREDIT
from fil.stages import site
from fil.stages.gallery_pages import GalleryContent

SITE_SOURCES = Path(site.__file__).resolve().parents[1] / "site"
_SVG = '<svg class="va va-akala_1" viewBox="0 0 120 72"><path d="M0 0"/></svg>'


@pytest.fixture(scope="module")
def texts() -> dict[str, dict]:
    if shutil.which("node") is None:
        pytest.skip("node is not installed")
    return interface_text.load()


def _language(code: str):
    return next(language for language in LANGUAGES if language.code == code)


def _verb(slug: str, arabic: str, root: str, bs: str, en: str, rank: int) -> Word:
    return Word(id=word_id("verb", slug), arabic=arabic, root=root, meaning=B(bs, en), rank=rank, sound=f"audio/{slug}.m4a")


_VERBS = (_verb("akala", "أَكَلَ", "أكل", "jesti", "to eat", 1), _verb("shariba", "شَرِبَ", "شرب", "piti", "to drink", 2),
          _verb("kataba", "كَتَبَ", "كتب", "pisati", "to write", 3), _verb("fataha", "فَتَحَ", "فتح", "otvoriti", "to open", 4),
          _verb("ta-ama", "طَعِمَ", "طعم", "jesti, kušati", "to eat, to taste", 5))


# ---------- Animacija → glagol ----------

def test_a_drawn_verb_is_asked_by_its_animation_among_verbs_named_by_arabic_and_meaning():
    exercises = animation_exercises(_VERBS, {"verb:akala": _SVG})
    assert len(exercises) == 1                                        # only the drawn verbs are asked
    asked = exercises[0]
    assert asked.kind == ANIMATION and asked.animation == _SVG and asked.words == ("verb:akala",)
    assert asked.answer_sound == "audio/akala.m4a" and asked.answer_word == "أَكَلَ"
    assert len(asked.options) == 4 and all(option.arabic and option.meaning for option in asked.options)
    assert asked.correct[0].meaning == B("jesti", "to eat")
    offered = {option.meaning.en for option in asked.options}
    assert "to eat, to taste" not in offered                          # never a verb of the same meaning
    gate.check(exercises)


def test_a_drawn_verb_without_three_fair_distractors_is_not_asked():
    assert animation_exercises(_VERBS[:3], {"verb:akala": _SVG}) == []


def test_an_option_named_by_both_is_read_as_its_arabic_and_its_meaning():
    option = Option(True, arabic="أَكَلَ", meaning=B("jesti", "to eat"))
    assert option.sort == "arabic" and option.as_json() == {"ar": "أَكَلَ", "bs": "jesti", "en": "to eat"}
    asked = animation_exercises(_VERBS, {"verb:akala": _SVG})[0].as_json()
    assert asked["animation"] == _SVG and asked["answerSound"] == "audio/akala.m4a"


def test_the_animation_kind_follows_the_picture_kind_and_is_named_in_both_exercise_languages(texts):
    assert KINDS.index(ANIMATION) == KINDS.index(PICTURE) + 1
    for code in exercise_render.EXERCISE_LANGUAGES:
        about = texts[code]["exercisePage"]["kinds"][ANIMATION]
        assert all(about[field] for field in ("name", "slug", "intro", "question")), code
    assert texts["bs"]["exercisePage"]["kinds"][ANIMATION]["slug"] != texts["en"]["exercisePage"]["kinds"][ANIMATION]["slug"]


def test_the_animation_exercise_page_replays_its_drawings(texts):
    counts, shards = {ANIMATION: 12}, {ANIMATION: 1}
    html = exercise_render.kind_page(ANIMATION, _language("en"), texts, counts, shards, published={render.EXERCISES},
                                     picture_credit=OWN_DRAWINGS_CREDIT)
    assert html.index('src="../../../animation.js"') < html.index('src="../../../exercises.js"')
    assert OWN_DRAWINGS_CREDIT in html
    picture = exercise_render.kind_page(PICTURE, _language("en"), texts, {PICTURE: 3}, {PICTURE: 1}, published=set())
    assert "animation.js" not in picture


def test_the_exercise_script_draws_the_animation_and_names_each_verb_by_both():
    script = (SITE_SOURCES / "exercises.js").read_text(encoding="utf-8")
    assert "if (item.animation) box.append(drawing(item.animation));" in script
    assert '"verb-anim exercise-animation"' in script                 # site/animation.js replays it on tap
    assert "voiceDrawing(item);" in script                            # once answered, a tap says the verb


# ---------- the galleries lead to their exercise ----------

def test_each_gallery_has_a_practise_button_into_its_exercise(texts):
    items = gallery_render.verb_items([render.PublishedVerb({"rank": 1, "root": "أكل", "form": 1, "lemma": "أَكَلَ",
                                                             "meaning": {"en": "to eat", "bs": "jesti"}}, "akala")],
                                      lambda card: _SVG)
    content = GalleryContent(gallery_render.ANIMATION_GALLERY, tuple(items),
                             {"bs": "bs/vjezbe/animacija-glagol/", "en": "en/exercises/animation-verb/"})
    assert content.practice_in("bs") == "bs/vjezbe/animacija-glagol/"
    assert content.practice_in("tr") == "en/exercises/animation-verb/"     # the exercises are in Bosnian and English
    html = gallery_render.gallery_page(content.gallery, items, _language("bs"), texts["bs"],
                                       practice_path=content.practice_in("bs"))
    assert '<a class="button gallery-practise" href="../../bs/vjezbe/animacija-glagol/">Vježbaj →</a>' in html
    assert "gallery-practise" not in gallery_render.gallery_page(content.gallery, items, _language("bs"), texts["bs"])
    assert GalleryContent(gallery_render.ANIMATION_GALLERY, ()).practice_in("en") is None


def test_every_language_names_the_practise_button(texts):
    assert all(texts[code]["galleryPage"]["practise"] for code in CODES)


# ---------- the galleries in the top bar ----------

def test_the_top_bar_of_every_page_leads_to_both_galleries_in_every_language(texts):
    for code in CODES:
        bar = render.top_bar(texts[code], "../", _language(code), lambda language: f"{language}/", section=render.VERBS)
        nav = texts[code]["aboutNav"]
        assert f'<a href="../{code}/animations/">{nav["animations"]}</a>' in bar, code
        assert f'<a href="../{code}/noun-pictures/">{nav["pictures"]}</a>' in bar, code


def test_a_gallery_marks_itself_current_in_the_top_bar(texts):
    html = gallery_render.gallery_page(gallery_render.ANIMATION_GALLERY, [], _language("en"), texts["en"])
    assert '<a href="../../en/animations/" aria-current="page">Animations</a>' in html


def test_the_app_header_leads_to_both_galleries():
    app = (SITE_SOURCES / "index.html").read_text(encoding="utf-8")
    assert '<a id="animations-link"></a><a id="pictures-link"></a></nav>' in app
    assert "renderGalleryLinks(ui);" in app
