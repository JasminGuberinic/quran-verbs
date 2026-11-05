"""The gate every noun picture passes before it ships, and the minifier that precedes it.

A picture reaches a learner's page inline or as a file, so it must be inert and small: a
well-formed SVG, nothing executable, nothing fetched from elsewhere, only our palette's
colours (one family of pictures, legible on the dark background), at most 8 KB.

Pure: text in, problems out.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ElementTree

from fil.nouns.palette import Palette, paint_values

MAX_BYTES = 8 * 1024
SVG_NAMESPACE = "{http://www.w3.org/2000/svg}"
_COLOURLESS = frozenset({"none"})
# Markup that runs code, pulls in other documents, or styles past the paint attributes.
_FORBIDDEN = {
    "a script": re.compile(r"<script\b", re.I),
    "a foreign object": re.compile(r"<foreignObject\b", re.I),
    "an event handler": re.compile(r"\son[a-z]+\s*=", re.I),
    "a DOCTYPE or entity": re.compile(r"<!(?:DOCTYPE|ENTITY)", re.I),
    "an external reference": re.compile(r"""\b(?:xlink:)?href\s*=\s*["'](?!#)|url\(\s*["']?(?!#)""", re.I),
    "a style": re.compile(r"<style\b|\sstyle\s*=", re.I),
    "an image": re.compile(r"<image\b", re.I),
}


def picture_problems(svg: str, palette: Palette) -> list[str]:
    """Everything that keeps `svg` from shipping; empty when it may."""
    problems = [f"is {size:,} bytes (max {MAX_BYTES:,})" for size in [len(svg.encode("utf-8"))] if size > MAX_BYTES]
    problems += [f"contains {what}" for what, pattern in _FORBIDDEN.items() if pattern.search(svg)]
    if any(problem.startswith("contains a DOCTYPE") for problem in problems):
        return problems                    # never hand an entity to the parser
    problems += _structure_problems(svg)
    problems += [f"uses colour {value!r} outside the palette" for value in sorted(set(paint_values(svg)))
                 if value.lower() not in palette.colours | _COLOURLESS]
    return problems


def minified(svg: str) -> str:
    """`svg` without its XML declaration, comments, ids, metadata and layout whitespace."""
    text = re.sub(r"<\?xml[^>]*\?>|<!--.*?-->", "", svg, flags=re.S)
    text = re.sub(r"<(metadata|title|desc)\b.*?</\1>", "", text, flags=re.S)
    text = re.sub(r'\s(?:id|stroke-miterlimit|version|xml:space|sodipodi:[a-z]+|xmlns:sodipodi)="[^"]*"', "", text)
    text = re.sub(r">\s+<", "><", text)
    return re.sub(r"\s+", " ", text).strip()


def _structure_problems(svg: str) -> list[str]:
    try:
        root = ElementTree.fromstring(svg)
    except ElementTree.ParseError as error:
        return [f"is not well-formed XML ({error})"]
    if root.tag != f"{SVG_NAMESPACE}svg":
        return [f"root element is {root.tag!r}, not an SVG"]
    if "viewBox" not in root.attrib:
        return ["has no viewBox (cannot scale to 64 px)"]
    return []
