"""The particles' data file: read and validated on the way in.

    data/particles.json   {"<slug>": {"arabic", "lemma", "count", "meaning", "grammar", "uses": [...], ...}}

A small I/O adapter; what a particle must hold is decided in fil.particles.model.
"""

from __future__ import annotations

import json
from pathlib import Path

from fil.particles.model import Particle, parse_particles
from fil.resources import PARTICLES_JSON

_ABOUT = "_about"


def load_particles(path: Path = PARTICLES_JSON) -> tuple[Particle, ...]:
    """Every particle, validated (fil.particles.model.InvalidParticleData); none when there is no file."""
    if not path.exists():
        return ()
    entries = json.loads(path.read_text(encoding="utf-8"))
    return parse_particles({slug: entry for slug, entry in entries.items() if slug != _ABOUT})
