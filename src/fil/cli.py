"""Single entry point for the content engine.

    fil <stage>

One coherent command instead of a pile of scripts. Each stage is a small module;
this is just the façade that names and dispatches them.
"""

from __future__ import annotations

import argparse

from fil.stages import (
    agenda,
    audio_build,
    bundle,
    coverage,
    dataset,
    full,
    ingest,
    package,
    review,
)

# stage name -> (function, one-line description)
_STAGES = {
    "ingest": (ingest.main, "parse the Quranic Arabic Corpus → verb catalogue"),
    "agenda": (agenda.main, "plan the sentences the factory owes; report every job's state"),
    "dataset": (dataset.main, "authored verbs.yaml → conjugations (build/verbs.json)"),
    "audio": (audio_build.main, "generate + QA the per-form audio clips"),
    "package": (package.main, "package the audio-gated content.sqlite (legacy audio path)"),
    "bundle": (bundle.main, "package content.sqlite from the service (conjugations + examples + ayāt)"),
    "all": (full.main, "dataset → audio → package (the full bundle)"),
    "coverage": (coverage.main, "reconcile every Quranic verb; print agreement rate"),
    "review": (review.main, "export the review queue of generator↔Quran conflicts"),
}


def main() -> None:
    parser = argparse.ArgumentParser(prog="fil", description=__doc__)
    stages = parser.add_subparsers(dest="stage", required=True, metavar="stage")
    for name, (_run, description) in _STAGES.items():
        stages.add_parser(name, help=description)

    stage = parser.parse_args().stage
    _STAGES[stage][0]()


if __name__ == "__main__":
    main()
