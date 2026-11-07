"""The verb animations on disk: the list, the SVG sources, the gate, the shipped SVGs.

The only I/O of the animation feature; the rig and the gate are pure.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from fil.animations import gate
from fil.animations.rig import expand
from fil.resources import MEANINGS_JSON, VERB_ANIMATIONS_DIR, VERB_ANIMATIONS_JSON

_SOURCE_SUFFIX = ".svg"


class AnimationRejected(ValueError):
    """An animation failed its gate: nothing that fails ships."""


@dataclass(frozen=True)
class VerbAnimation:
    key: str     # root_form, as in data/meanings.json
    stem: str    # its file in data/verb_animations
    why: str     # what it shows, for the reviewer
    svg: str     # the shipped SVG: rig drawn in, shared look added, minified


def verb_key(card: Mapping) -> str:
    return f"{card['root']}_{card['form']}"


@lru_cache(maxsize=1)
def load_animations() -> Mapping[str, VerbAnimation]:
    """Every animation by verb key, each gated; AnimationRejected lists everything wrong at once."""
    return load_from(VERB_ANIMATIONS_JSON, VERB_ANIMATIONS_DIR, MEANINGS_JSON)


def load_from(manifest_path: Path, directory: Path, meanings_path: Path) -> Mapping[str, VerbAnimation]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    meanings = json.loads(meanings_path.read_text(encoding="utf-8"))
    sources = {path.stem: path.read_text(encoding="utf-8") for path in sorted(directory.glob(f"*{_SOURCE_SUFFIX}"))}
    shipped = {stem: expand(source, stem) for stem, source in sources.items()}
    problems = [
        *gate.manifest_problems(manifest, {key: entry["en"] for key, entry in meanings.items()}, sources),
        *[f"{stem}: {problem}" for stem, svg in shipped.items() for problem in gate.svg_problems(svg)],
        *gate.keyframe_clashes(shipped),
    ]
    if problems:
        raise AnimationRejected("\n".join(problems))
    return {key: VerbAnimation(key, entry["file"], entry["why"], shipped[entry["file"]]) for key, entry in manifest.items()}


def animation_of(card: Mapping) -> str:
    """The card's shipped SVG, or "" for a verb nothing is drawn for."""
    found = load_animations().get(verb_key(card))
    return found.svg if found else ""
