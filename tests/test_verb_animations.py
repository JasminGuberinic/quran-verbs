"""Verb animations: the gate every drawing passes, the rig, and how a page shows one.

The last tests are the shipping gate over the real data: every animation is of a studied verb
whose card may be drawn, is inert, uses only the two site colours and is small.
"""

from __future__ import annotations

import json

import pytest

from fil.animations import gate
from fil.animations.library import AnimationRejected, animation_of, load_animations, load_from
from fil.animations.rig import UnknownRigTag, expand
from fil.pages import render
from fil.pages.animation_render import OWN_DRAWINGS_CREDIT, animation_block, credit_with
from fil.pages.render import PublishedVerb
from fil.resources import MEANINGS_JSON
from test_pages import _card, _language, _text

SOURCE = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 72"><style>@keyframes zz-a{from{opacity:0}}'
          '& .ra{animation:zz-a 1s both}</style><path class="p" d="M0 0h5"/><rig x="60" y="44"/></svg>')


# ---------------------------------------------------------------- the rig

def test_the_rig_draws_one_faceless_figure_with_its_limbs():
    svg = expand(SOURCE, "zz")
    assert "<rig" not in svg and svg.count('class="ra"') == 1
    assert svg.count("<circle") == 1                      # a head, and nothing on it
    assert "ellipse" not in svg and "eye" not in svg


def test_the_styles_are_scoped_to_their_verb_and_reduced_motion_stops_them():
    svg = expand(SOURCE, "zz")
    assert svg.startswith('<svg class="va va-zz" ')
    assert ".va-zz .ra{" in svg
    assert "prefers-reduced-motion:reduce){.va-zz,.va-zz *{animation:none!important}}" in svg
    assert gate.svg_problems(svg) == []


def test_a_prop_is_placed_in_the_limb_it_is_given():
    held = SOURCE.replace('<rig x="60" y="44"/>', '<rig x="60" y="44"><in at="ra"><circle class="q" r="2"/></in></rig>')
    assert '<g class="ra"><circle class="q" r="2"/>' in expand(held, "zz")


def test_a_rig_the_expander_does_not_understand_is_refused():
    with pytest.raises(UnknownRigTag):
        expand(SOURCE.replace('<rig x="60" y="44"/>', '<rig y="44"/>'), "zz")


# ---------------------------------------------------------------- the gate

@pytest.mark.parametrize("meaning", ["to make God's partners", "to be Lord", "to kill", "to die", "to slaughter",
                                     "to believe", "to deny", "to destroy", "to stone", "to perish"])
def test_what_the_card_says_about_god_death_or_belief_is_never_drawn(meaning):
    assert gate.undrawable_word(meaning)


@pytest.mark.parametrize("meaning", ["to go out, to leave", "to sit", "to eat", "to give", "to push, to repel, to pay",
                                     "to know", "to fear", "to love", "to think", "to fight", "to pray",
                                     "to prostrate oneself", "to bow (in prayer)", "to fast", "to recite",
                                     "to create", "to send down, to reveal", "to forgive", "to guide", "to bless"])
def test_a_plain_action_may_be_drawn(meaning):
    assert gate.undrawable_word(meaning) is None


@pytest.mark.parametrize("markup, problem", [
    ("<text>x</text>", "<text>"), ("<image/>", "<image>"), ("<script/>", "<script>"), ("<a/>", "<a>"),
    ('<use href="#x"/>', "link"), ('<path onclick="x()"/>', "event handler"), ('<path style="fill:red"/>', "style attribute"),
    ('<path fill="#ff0000"/>', "colour"), ('<path fill="red"/>', "'red'"), ('<path stroke="url(#g)"/>', "link"),
])
def test_a_drawing_that_is_not_inert_or_off_palette_is_refused(markup, problem):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg">{markup}</svg>'
    assert any(problem in found for found in gate.svg_problems(svg))


def test_the_two_site_tokens_and_none_are_the_only_paints():
    ok = '<svg xmlns="http://www.w3.org/2000/svg"><path fill="var(--accent)" stroke="var(--gold)"/><path fill="none"/></svg>'
    assert gate.svg_problems(ok) == []


def test_a_drawing_over_the_size_limit_is_refused():
    big = '<svg xmlns="http://www.w3.org/2000/svg">' + "<path/>" * 600 + "</svg>"
    assert any("limit" in found for found in gate.svg_problems(big))


def test_the_list_is_checked_against_the_studied_verbs_and_the_files():
    meanings = {"a_1": "to sit", "b_1": "to die"}
    manifest = {"a_1": {"file": "one", "why": "sits"}, "b_1": {"file": "two", "why": "makes"},
                "c_1": {"file": "three", "why": "x"}, "a_2": {"file": "one", "why": ""}}
    problems = gate.manifest_problems(manifest, {**meanings, "a_2": "to sit"}, ["one", "orphan"])
    assert any("c_1: not a studied verb" in found for found in problems)
    assert any("b_1" in found and "never drawn" in found for found in problems)
    assert any("a_2" in found and "why" in found for found in problems)
    assert "one: listed twice" in problems and "orphan: file is not in the list" in problems
    assert "two: listed but there is no file" in problems


def test_two_animations_may_not_share_a_keyframe_name():
    assert gate.keyframe_clashes({"a": "@keyframes k{}", "b": "@keyframes k{}"})
    assert not gate.keyframe_clashes({"a": "@keyframes k{}", "b": "@keyframes m{}"})


def test_loading_lists_every_problem_at_once(tmp_path):
    (tmp_path / "bad.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><style></style><text/></svg>')
    manifest = tmp_path / "list.json"
    manifest.write_text(json.dumps({"قول_1": {"file": "bad", "why": "x"}}), encoding="utf-8")
    with pytest.raises(AnimationRejected, match="<text> is not allowed"):
        load_from(manifest, tmp_path, MEANINGS_JSON)


# ---------------------------------------------------------------- the shipped data

def test_every_shipped_animation_passes_the_gate_and_is_small():
    animations = load_animations()
    assert 100 <= len(animations) <= 600
    for animation in animations.values():
        assert gate.svg_problems(animation.svg) == [], animation.key
        assert len(animation.svg.encode("utf-8")) <= gate.MAX_BYTES, animation.key


def test_every_animated_verb_is_a_studied_plain_action():
    meanings = json.loads(MEANINGS_JSON.read_text(encoding="utf-8"))
    for key in load_animations():
        assert key in meanings
        assert gate.undrawable_word(meanings[key]["en"]) is None, key


def test_every_animation_says_what_it_shows():
    assert all(animation.why.endswith(".") for animation in load_animations().values())


# ---------------------------------------------------------------- on the page

def _animated_card() -> dict:
    return {**_card(), "root": "قعد", "form": 1}


def test_a_verb_with_an_animation_shows_it_hidden_from_assistive_technology_beside_its_meaning():
    card = _animated_card()
    html = render.verb_page(PublishedVerb(card, "qaada"), _language("bs"), _text(), animation=animation_of(card))
    assert '<div class="verb-anim" aria-hidden="true"><svg class="va va-qaada_1"' in html
    assert html.index("verb-anim") > html.index('class="meaning"')
    assert 'animation.js" defer></script>' in html
    assert OWN_DRAWINGS_CREDIT in html


def test_a_verb_without_an_animation_changes_nothing():
    html = render.verb_page(PublishedVerb(_card(), "qala"), _language("en"), _text())
    assert "verb-anim" not in html and "animation.js" not in html and OWN_DRAWINGS_CREDIT not in html


def test_the_own_drawings_credit_follows_the_picture_credit_and_only_when_shown():
    assert credit_with("<b>Pictures.</b> x", "<svg/>") == f"<b>Pictures.</b> x {OWN_DRAWINGS_CREDIT}"
    assert credit_with("<b>Pictures.</b> x", "") == "<b>Pictures.</b> x"
    assert animation_block("") == ""
