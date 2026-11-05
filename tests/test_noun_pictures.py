"""Noun categories and pictures: the recolouring, the gate, the data files, the credit line.

The last tests are the shipping gate: every picture the manifest names exists, is a valid
inert SVG in our palette only, and is small — no picture reaches a learner otherwise.
"""

from __future__ import annotations

import pytest

from fil.noun_pictures import load_categories, load_pictures
from fil.nouns.categories import CATEGORIES, NEVER_PICTURED, NounCategoryFormatError, parse_categories, picturable
from fil.nouns.palette import SITE_PALETTE, Palette, fill_colours, lightness, normalised, recolour, tone_map
from fil.nouns.picture_gate import MAX_BYTES, minified, picture_problems
from fil.nouns.pictures import OPENMOJI, TWEMOJI, PictureManifestError, parse_manifest, shown, sources_used
from fil.pages.picture_credits import picture_credit
from fil.resources import NOUN_PICTURES_DIR

PALETTE = Palette(light="#cccccc", mid="#888888", dark="#111111")
CATEGORY = {"lemma": "نَاقَة", "root": "نوق", "gloss_en": "she-camel", "category": "animals", "picturable": True}
PICTURE = {"lemma": "نَاقَة", "root": "نوق", "slug": "naqa", "bs": "deva", "codepoint": "1F42A", "source": "openmoji"}


def svg(body: str) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 72 72">{body}</svg>'


# ---------------------------------------------------------------- palette

def test_colours_are_normalised_to_six_digit_lowercase_hex():
    assert normalised("#ABC") == "#aabbcc"
    assert normalised("#F4AA41ff") == "#f4aa41"
    assert normalised("black") == "#000000"
    assert normalised("none") is None and normalised("url(#g)") is None


def test_three_lightness_groups_take_dark_mid_light_in_order():
    tones = tone_map({"#202020", "#252525", "#808080", "#858585", "#f0f0f0"}, PALETTE)
    assert tones["#202020"] == tones["#252525"] == PALETTE.dark
    assert tones["#808080"] == tones["#858585"] == PALETTE.mid
    assert tones["#f0f0f0"] == PALETTE.light


def test_two_groups_keep_dark_free_for_outlines_and_one_colour_is_mid():
    assert tone_map({"#808080", "#f0f0f0"}, PALETTE) == {"#808080": PALETTE.mid, "#f0f0f0": PALETTE.light}
    assert tone_map({"#f4aa41"}, PALETTE) == {"#f4aa41": PALETTE.mid}


def test_near_black_fills_and_every_stroke_become_the_dark_tone():
    recoloured = recolour(svg('<path fill="#000" stroke="#ffffff"/><path fill="#f4aa41" stroke="#f4aa41"/>'), PALETTE)
    assert recoloured.count(f'stroke="{PALETTE.dark}"') == 2
    assert f'fill="{PALETTE.dark}"' in recoloured and f'fill="{PALETTE.mid}"' in recoloured


def test_unfilled_shapes_inherit_the_dark_tone_from_the_root_and_none_stays_none():
    recoloured = recolour(svg('<path d="M0 0"/><path fill="none" stroke="red"/>'), PALETTE)
    assert recoloured.startswith(f'<svg fill="{PALETTE.dark}"')
    assert 'fill="none"' in recoloured


def test_a_recoloured_icon_uses_only_palette_colours():
    original = svg('<path fill="#C1694F"/><path fill="#E6E7E8"/><circle fill="#292F33"/><path stroke="#000"/>')
    assert fill_colours(recolour(original, PALETTE)) <= PALETTE.colours


def test_perceived_lightness_orders_black_below_white():
    assert lightness("#000000") == 0 and lightness("#ffffff") == pytest.approx(1)


# ---------------------------------------------------------------- gate

def test_a_clean_palette_svg_passes_the_gate():
    assert picture_problems(svg(f'<path fill="{SITE_PALETTE.mid}" stroke="{SITE_PALETTE.dark}"/>'), SITE_PALETTE) == []


@pytest.mark.parametrize("body, problem", [
    ('<script>alert(1)</script>', "a script"),
    ('<path onclick="x()" fill="none"/>', "an event handler"),
    ('<image href="https://example.com/a.png"/>', "an external reference"),
    ('<path fill="url(https://example.com/#g)"/>', "an external reference"),
    ('<path style="fill:#a6e3d0"/>', "a style"),
    ('<foreignObject/>', "a foreign object"),
])
def test_the_gate_refuses_anything_active_or_external(body, problem):
    assert any(problem in found for found in picture_problems(svg(body), SITE_PALETTE))


def test_the_gate_refuses_foreign_colours_size_and_broken_markup():
    assert any("outside the palette" in found for found in picture_problems(svg('<path fill="#ff0000"/>'), SITE_PALETTE))
    big = svg(f'<path fill="none" d="{"M0 0 " * MAX_BYTES}"/>')
    assert any("bytes" in found for found in picture_problems(big, SITE_PALETTE))
    assert any("well-formed" in found for found in picture_problems(svg("<path>"), SITE_PALETTE))
    assert any("DOCTYPE" in found for found in picture_problems('<!DOCTYPE x [<!ENTITY a "b">]>' + svg(""), SITE_PALETTE))


def test_minifying_drops_ids_comments_and_layout_whitespace_but_keeps_the_drawing():
    original = '<?xml version="1.0"?>\n<svg id="emoji" viewBox="0 0 72 72" xmlns="http://www.w3.org/2000/svg">\n' \
               '  <!-- colour -->\n  <g id="color">\n    <path fill="#a6e3d0" d="M1 2"/>\n  </g>\n</svg>\n'
    assert minified(original) == ('<svg viewBox="0 0 72 72" xmlns="http://www.w3.org/2000/svg">'
                                  '<g><path fill="#a6e3d0" d="M1 2"/></g></svg>')


# ---------------------------------------------------------------- categories

def test_categories_parse_and_index_by_lemma_and_root():
    entries = parse_categories([CATEGORY])
    assert entries[("نَاقَة", "نوق")].is_picturable


@pytest.mark.parametrize("change", [{"category": "fruit"}, {"picturable": "yes"}, {"gloss_en": " "},
                                    {"category": "people_family"}])
def test_a_bad_category_entry_fails_fast(change):
    with pytest.raises(NounCategoryFormatError):
        parse_categories([{**CATEGORY, **change}])


def test_a_lemma_listed_twice_fails_fast():
    with pytest.raises(NounCategoryFormatError):
        parse_categories([CATEGORY, CATEGORY])


def test_every_catalogued_lemma_has_a_known_category_and_people_are_never_pictured():
    entries = load_categories()
    assert len(entries) >= 3000
    assert {entry.category for entry in entries.values()} == set(CATEGORIES)
    assert not any(entry.category in NEVER_PICTURED for entry in picturable(entries.values()))


@pytest.mark.parametrize("lemma, is_picturable", [("عِنَب", True), ("جَبَل", True), ("يَد", True),
                                                   ("عَرْش", False), ("رَبّ", False), ("صُور", False)])
def test_golden_picturability(lemma, is_picturable):
    found = [entry for entry in load_categories().values() if entry.lemma == lemma]
    assert found and all(entry.is_picturable is is_picturable for entry in found), lemma


# ---------------------------------------------------------------- manifest

def test_a_manifest_entry_must_name_a_picturable_noun():
    categories = parse_categories([{**CATEGORY, "picturable": False}])
    with pytest.raises(PictureManifestError):
        parse_manifest([PICTURE], categories)


@pytest.mark.parametrize("change", [{"source": "noto"}, {"slug": "nāqa"}, {"codepoint": ""}])
def test_a_bad_manifest_entry_fails_fast(change):
    with pytest.raises(PictureManifestError):
        parse_manifest([{**PICTURE, **change}], parse_categories([CATEGORY]))


def test_a_noun_without_a_fitting_emoji_has_no_picture():
    [picture] = parse_manifest([{**PICTURE, "codepoint": "", "source": None}], parse_categories([CATEGORY]))
    assert not picture.has_picture and shown([picture]) == []


# ---------------------------------------------------------------- credit

def test_the_credit_names_only_the_sets_shown_with_licence_links():
    [picture] = parse_manifest([PICTURE], parse_categories([CATEGORY]))
    credit = picture_credit(sources_used([picture]))
    assert 'href="https://openmoji.org"' in credit and 'href="https://creativecommons.org/licenses/by-sa/4.0/"' in credit
    assert "recoloured" in credit and "Twemoji" not in credit


def test_both_sets_are_credited_with_their_own_licence_and_no_pictures_need_no_credit():
    credit = picture_credit([OPENMOJI, TWEMOJI])
    assert "CC BY-SA 4.0" in credit and "CC BY 4.0" in credit and "jdecked/twemoji" in credit
    assert picture_credit([]) == ""


# ---------------------------------------------------------------- shipping gate

def test_every_chosen_picture_ships_valid_inert_small_and_in_our_palette():
    pictures = shown(load_pictures())
    assert pictures
    for picture in pictures:
        path = NOUN_PICTURES_DIR / picture.file_name
        assert path.is_file(), picture.slug
        assert picture_problems(path.read_text(encoding="utf-8"), SITE_PALETTE) == [], picture.slug


def test_only_chosen_pictures_are_shipped():
    expected = {picture.file_name for picture in shown(load_pictures())}
    assert {path.name for path in NOUN_PICTURES_DIR.glob("*")} == expected


def test_minifying_rounds_coordinates_to_a_tenth_but_leaves_colours_alone():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 36 36"><path fill="#52c2a6" d="M21.388.62c-1.852 0 4.5 7"/></svg>'

    assert minified(svg) == ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 36 36">'
                             '<path fill="#52c2a6" d="M21.3.62c-1.8 0 4.5 7"/></svg>')
