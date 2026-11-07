"""The gate every verb animation passes before it ships.

An animation is a picture of what a verb means, so it must (1) belong to a studied verb whose
meaning may be drawn — never God Himself, killing or death; His acts only by their effect,
worship and feelings only by a faceless figure's posture; (2) be inert (no script, text, image or link), (3) use only the two
colour tokens of the site, and (4) stay small.

Pure: text in, problems out.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ElementTree
from collections.abc import Collection, Iterable, Mapping

from fil.animations.tokens import PAINTS

MAX_BYTES = 3 * 1024
_NAMESPACE = "{http://www.w3.org/2000/svg}"
_ELEMENTS_NEVER = frozenset({"text", "tspan", "image", "script", "foreignObject", "a", "use", "title", "desc", "iframe"})
_MARKUP_NEVER = {
    "an event handler": re.compile(r"\son[a-z]+\s*=", re.I),
    "a DOCTYPE or entity": re.compile(r"<!(?:DOCTYPE|ENTITY)", re.I),
    "a link or external reference": re.compile(r"\b(?:xlink:)?href\s*=|url\(|@import|javascript:", re.I),
    "a style attribute": re.compile(r"\sstyle\s*=", re.I),
    "a colour that is not a site token": re.compile(r"#[0-9a-f]{3,8}\b|\b(?:rgb|hsl)a?\(", re.I),
}
_PAINT = re.compile(r"\b(?:fill|stroke)\s*[:=]\s*[\"']?(?P<value>[^;}\"'\s>/]+(?:\([^)]*\))?)")
_KEYFRAMES = re.compile(r"@keyframes\s+([\w-]+)")

# What the studied card says, in English, that makes a verb undrawable: God Himself (never
# pictured in any form), killing and death, and belief itself, which has no honest picture.
# Everything else may be drawn symbolically and faceless: worship by a figure on a prayer mat,
# God's acts only by their effect (rain falling, a seed sprouting), feelings by posture.
# Matched as word beginnings, so "lordship" is "lord".
UNDRAWABLE_MEANINGS = ("god", "allah", "lord", "throne", "kill", "slaughter", "massacre", "stone", "crucif", "destroy",
                       "perish", "die", "death", "believ", "deny", "disbelieve")
_UNDRAWABLE = re.compile(r"\b(?:" + "|".join(map(re.escape, UNDRAWABLE_MEANINGS)) + ")", re.I)


def undrawable_word(meaning: str) -> str | None:
    """The first word of the card's meaning that forbids a picture, or None."""
    found = _UNDRAWABLE.search(meaning)
    return found.group(0) if found else None


def svg_problems(svg: str) -> list[str]:
    """What is wrong with one shipped (expanded) SVG; empty when it may ship."""
    problems = [f"{name} is not allowed" for name, pattern in _MARKUP_NEVER.items() if pattern.search(svg)]
    problems += [f"paint {value!r} is not a site token" for value in sorted(_foreign_paints(svg))]
    problems += _size_problems(svg)
    return problems + _structure_problems(svg)


def keyframe_names(svg: str) -> frozenset[str]:
    return frozenset(_KEYFRAMES.findall(svg))


def manifest_problems(manifest: Mapping[str, Mapping[str, str]], meanings_en: Mapping[str, str],
                      stems_on_disk: Collection[str]) -> list[str]:
    """What is wrong with the list of animated verbs against the studied meanings and the files."""
    listed = [entry.get("file", "") for entry in manifest.values()]
    return [
        *[problem for key, entry in sorted(manifest.items()) for problem in _entry_problems(key, entry, meanings_en)],
        *[f"{stem}: listed twice" for stem in sorted({stem for stem in listed if listed.count(stem) > 1})],
        *[f"{stem}: file is not in the list" for stem in sorted(set(stems_on_disk) - set(listed))],
        *[f"{stem}: listed but there is no file" for stem in sorted(set(listed) - set(stems_on_disk))],
    ]


def keyframe_clashes(svg_by_stem: Mapping[str, str]) -> list[str]:
    """Keyframe names are page-wide, so two animations on one page must never share one."""
    owner: dict[str, str] = {}
    clashes = []
    for stem, svg in sorted(svg_by_stem.items()):
        for name in sorted(keyframe_names(svg)):
            if name in owner:
                clashes.append(f"keyframes {name!r} are in both {owner[name]} and {stem}")
            owner.setdefault(name, stem)
    return clashes


def _entry_problems(key: str, entry: Mapping[str, str], meanings_en: Mapping[str, str]) -> Iterable[str]:
    if key not in meanings_en:
        yield f"{key}: not a studied verb"
        return
    if not entry.get("why", "").strip():
        yield f"{key}: says nothing about what it shows (why)"
    word = undrawable_word(meanings_en[key])
    if word:
        yield f"{key}: the card's meaning {meanings_en[key]!r} has {word!r}; that is never drawn"


def _foreign_paints(svg: str) -> set[str]:
    return {found["value"] for found in _PAINT.finditer(svg) if found["value"] not in PAINTS}


def _size_problems(svg: str) -> list[str]:
    size = len(svg.encode("utf-8"))
    return [f"{size} bytes is over the {MAX_BYTES} limit"] if size > MAX_BYTES else []


def _structure_problems(svg: str) -> list[str]:
    try:
        root = ElementTree.fromstring(svg)
    except ElementTree.ParseError as error:
        return [f"not well-formed SVG: {error}"]
    if root.tag != f"{_NAMESPACE}svg":
        return ["the root is not an <svg>"]
    forbidden = {element.tag.removeprefix(_NAMESPACE) for element in root.iter()} & _ELEMENTS_NEVER
    return [f"<{name}> is not allowed" for name in sorted(forbidden)]
