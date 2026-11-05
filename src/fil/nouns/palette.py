"""Recolour an emoji SVG into the site's two or three greens.

A noun picture is an open-licence emoji (OpenMoji or Twemoji) redrawn in our palette so
every picture looks like one family. The emoji's own colours carry its shape — a lighter
rind, a darker seed — so what survives is their *order*: an icon's distinct fill colours
are ranked by lightness and split into up to three groups at the largest lightness gaps,
darkest group → dark tone, lightest → light. Near-black fills (outlines, pupils) and every
stroke become the dark tone; a shape with no fill, black by SVG default, does too.

Pure: text in, text out; no file is touched here.
"""

from __future__ import annotations

import colorsys
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

NAMED_COLOURS: Mapping[str, str] = {
    "black": "#000000", "white": "#ffffff", "red": "#ff0000", "green": "#008000", "blue": "#0000ff",
    "yellow": "#ffff00", "gray": "#808080", "grey": "#808080", "navy": "#000080",
}
NEAR_BLACK = 0.12   # below this lightness a fill is an outline or a pupil: always the dark tone
_PAINT_ATTRIBUTE = re.compile(r'\b(fill|stroke|stop-color|color)\s*=\s*"([^"]*)"')
_ROOT_WITHOUT_FILL = re.compile(r"<svg\b(?![^>]*\sfill=)")


@dataclass(frozen=True)
class Palette:
    light: str
    mid: str
    dark: str

    @property
    def colours(self) -> frozenset[str]:
        return frozenset({self.light, self.mid, self.dark})


# The site's greens (pages.css accents): light, mid, dark.
SITE_PALETTE = Palette(light="#a6e3d0", mid="#52c2a6", dark="#0f6b5c")


def recolour(svg: str, palette: Palette = SITE_PALETTE) -> str:
    """`svg` with every paint replaced by a palette tone (see the module docstring)."""
    tones = tone_map(fill_colours(svg), palette)

    def repaint(match: re.Match[str]) -> str:
        attribute, value = match.group(1), match.group(2)
        colour = normalised(value)
        if colour is None:
            return match.group(0)          # none / transparent / currentColor stay as they are
        tone = palette.dark if attribute == "stroke" else tones.get(colour, palette.dark)
        return f'{attribute}="{tone}"'

    repainted = _PAINT_ATTRIBUTE.sub(repaint, svg)
    return _ROOT_WITHOUT_FILL.sub(f'<svg fill="{palette.dark}"', repainted, count=1)


def fill_colours(svg: str) -> set[str]:
    """Every distinct fill colour of `svg`, as #rrggbb."""
    return {colour for attribute, value in _PAINT_ATTRIBUTE.findall(svg)
            if attribute != "stroke" and (colour := normalised(value))}


def paint_values(svg: str) -> list[str]:
    """Every fill/stroke/stop-color/color value written in `svg`, as written."""
    return [value for _, value in _PAINT_ATTRIBUTE.findall(svg)]


def tone_map(colours: Iterable[str], palette: Palette) -> dict[str, str]:
    """Each #rrggbb colour → the palette tone that keeps its place in the icon's light order."""
    colours = set(colours)
    near_black = {colour for colour in colours if lightness(colour) < NEAR_BLACK}
    ranked = sorted((colour for colour in colours - near_black), key=lightness)
    groups = _split_at_largest_gaps(ranked)
    tones = {colour: palette.dark for colour in near_black}
    for group, tone in zip(groups, _tones_for(len(groups), palette)):
        tones.update({colour: tone for colour in group})
    return tones


def normalised(value: str) -> str | None:
    """A colour value as lowercase #rrggbb, or None when it names no colour (none, url(...))."""
    colour = NAMED_COLOURS.get(value.strip().lower(), value.strip().lower())
    if not re.fullmatch(r"#(?:[0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})", colour):
        return None
    digits = colour[1:]
    if len(digits) in (3, 4):
        digits = "".join(digit * 2 for digit in digits[:3])
    return "#" + digits[:6]


def lightness(colour: str) -> float:
    """Perceived lightness 0..1: half HLS lightness, half luminance (both alone misrank greens)."""
    red, green, blue = (int(colour[index:index + 2], 16) / 255 for index in (1, 3, 5))
    luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    return (colorsys.rgb_to_hls(red, green, blue)[1] + luminance) / 2


def _split_at_largest_gaps(ranked: list[str]) -> list[list[str]]:
    """Colours in light order cut into at most three runs, at the two widest lightness gaps."""
    if len(ranked) < 2:
        return [ranked] if ranked else []
    gaps = sorted(range(1, len(ranked)), key=lambda index: lightness(ranked[index]) - lightness(ranked[index - 1]),
                  reverse=True)
    cuts = [0, *sorted(gaps[:2]), len(ranked)]
    return [ranked[start:end] for start, end in zip(cuts, cuts[1:])]


def _tones_for(group_count: int, palette: Palette) -> list[str]:
    """One group is mid; two are mid and light (dark stays for outlines); three use all."""
    return {0: [], 1: [palette.mid], 2: [palette.mid, palette.light],
            3: [palette.dark, palette.mid, palette.light]}[group_count]
