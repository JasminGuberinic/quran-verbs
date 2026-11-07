"""The shared figure and the shared look of every verb animation.

A verb's source file draws only what is special to it: a `<style>` with its keyframes, its
props, and `<rig x=".." y=".."/>` where the figure stands (x, y = the hip). The figure is one
faceless silhouette — head, torso, two arms, two legs — facing right, every limb hanging down
in its neutral pose and turning about its own joint (shoulders and hip). An `<in at="ra">`
inside the `<rig>` puts a prop into that part's group (the cup in the hand). Source styles
scope themselves with `&`, which becomes the verb's own class, so many animations can share
one page.

The pose a source gives its limbs and props is the FINAL one: animations only say where they
start from (`from{…}`), so a reader who prefers reduced motion sees the finished picture.

Pure: text in, text out.
"""

from __future__ import annotations

import re

from fil.animations.tokens import ACCENT, GOLD

VIEW_BOX = "0 0 120 72"
SCOPE_TOKEN = "&"
REPLAY_CLASS = "off"     # the player adds it for one frame: animations stop, then start over

_FIGURE = ('<g class="fig"><g class="ll">{ll}<path class="f" d="M0 0v17"/></g><g class="rl">{rl}<path class="f" d="M0 0v17"/></g>'
           '<g class="tr"><path class="f t" d="M0 0V-17"/><circle class="h" cy="-26" r="6.5"/>{tr}'
           '<g transform="translate(0 -15)"><g class="la">{la}<path class="f" d="M0 0v14"/></g></g>'
           '<g transform="translate(0 -15)"><g class="ra">{ra}<path class="f" d="M0 0v14"/></g></g></g></g>')

_BASE_CSS = (f".f,.p{{fill:none;stroke-linecap:round;stroke-linejoin:round}}.f{{stroke:{ACCENT};stroke-width:4.5}}"
             f".t{{stroke-width:8}}.h{{fill:{ACCENT}}}.p{{stroke:{GOLD};stroke-width:3}}.q{{fill:{GOLD}}}"
             f"&.{REPLAY_CLASS},&.{REPLAY_CLASS} *{{animation:none!important}}"
             "@media(prefers-reduced-motion:reduce){&,& *{animation:none!important}}")

_RIG_TAG = re.compile(r'<rig x="(?P<x>-?\d+)" y="(?P<y>-?\d+)"\s*(?:/>|>(?P<children>.*?)</rig>)', re.S)
_PROP = re.compile(r'<in at="(?P<at>ll|rl|tr|la|ra)">(?P<content>.*?)</in>', re.S)
_SLOTS = ("ll", "rl", "tr", "la", "ra")


class UnknownRigTag(ValueError):
    """A `<rig>` or `<in>` the expander does not understand."""


def scope_class(stem: str) -> str:
    return f"va-{stem}"


def expand(source: str, stem: str) -> str:
    """The shipped SVG: the source with its figure drawn in, the shared look added, scoped and minified."""
    drawn = _RIG_TAG.sub(_draw_figure, source)
    if "<rig" in drawn or "<in " in drawn:
        raise UnknownRigTag(f'{stem}: a rig must read <rig x="N" y="N"/> with only <in at="ra"> inside')
    styled = drawn.replace("</style>", _BASE_CSS + "</style>", 1)
    return _minified(styled.replace(SCOPE_TOKEN, f".{scope_class(stem)}"), stem)


def _draw_figure(found: re.Match) -> str:
    props = dict.fromkeys(_SLOTS, "")
    for prop in _PROP.finditer(found["children"] or ""):
        props[prop["at"]] += prop["content"]
    return f'<g transform="translate({found["x"]} {found["y"]})">{_FIGURE.format(**props)}</g>'


def _minified(svg: str, stem: str) -> str:
    """Whitespace and comments dropped, and the `<svg>` given its class, so each file is a little smaller."""
    uncommented = re.sub(r"<!--.*?-->", "", svg, flags=re.S)
    tight = re.sub(r">\s+<", "><", re.sub(r"\s+", " ", uncommented))
    tight = re.sub(r"\s*([{};,])\s*", r"\1", tight)
    return tight.replace("<svg ", f'<svg class="va {scope_class(stem)}" ', 1)
