"""Single entry point for the content engine.

    fil <stage>

One coherent command instead of a pile of scripts. Each stage is a small module;
this is just the façade that names and dispatches them.
"""

from __future__ import annotations

import argparse

from fil.stages import (
    adjectives,
    agenda,
    audio_build,
    batch,
    bundle,
    compose,
    coverage,
    dataset,
    evals,
    forms,
    full,
    i18n,
    ingest,
    nouns,
    nuances,
    package,
    pages,
    particles,
    review,
    roots,
    site,
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
    "evals": (evals.main, "report the factory's metrics; re-run the gate over the golden set"),
    "batch": (batch.main, "add verbs in batches: plan, wordbank, draft, meanings, ayah, review-export/import"),
    "site": (site.main, "build the static study site (build/site) for the verbs in data/meanings.json"),
    "i18n": (i18n.main, "translate into further languages via a translation memory: export, import, status"),
    "forms": (forms.main, "gloss every Quranic form of the studied verbs once per language: status, export, import"),
    "compose": (compose.main, "gloss the remaining Quranic forms by rule: status, sheets, paradigms, build, sample"),
    "nouns": (nouns.main, "the Quran's nouns and adjectives: status, catalogue, paradigms"),
    "adjectives": (adjectives.main, "the Quran's adjectives and their agreement: batch plan, meanings, tables, sentences"),
    "nuances": (nuances.main, "the Quran's near-synonyms (Nijanse): check the groups against the corpus, review-export"),
    "particles": (particles.main, "the Quran's particles (Čestice): frequency, find ayat, check the pages against the corpus"),
    "pronouns": (particles.pronouns_main, "the Quran's pronouns (Zamjenice): the same commands as `particles`"),
    "roots": (roots.main, "the root pages (Korijeni): check every studied word stands on its root page, show a root"),
    "pages": (pages.main, "build the public GitHub Pages site (build/pages); --deploy publishes it"),
}


def main() -> None:
    parser = argparse.ArgumentParser(prog="fil", description=__doc__)
    stages = parser.add_subparsers(dest="stage", required=True, metavar="stage")
    for name, (_run, description) in _STAGES.items():
        stages.add_parser(name, help=description)

    known, rest = parser.parse_known_args()
    if known.stage == "batch":
        batch.main(rest)
        return
    if known.stage == "i18n":
        i18n.main(rest)
        return
    if known.stage == "forms":
        forms.main(rest)
        return
    if known.stage == "compose":
        compose.main(rest)
        return
    if known.stage == "nouns":
        nouns.main(rest)
        return
    if known.stage == "adjectives":
        adjectives.main(rest)
        return
    if known.stage == "nuances":
        nuances.main(rest)
        return
    if known.stage == "particles":
        particles.main(rest)
        return
    if known.stage == "pronouns":
        particles.pronouns_main(rest)
        return
    if known.stage == "roots":
        roots.main(rest)
        return
    if known.stage == "pages":
        pages.main(rest)
        return
    if rest:
        parser.error(f"unrecognized arguments: {' '.join(rest)}")
    _STAGES[known.stage][0]()


if __name__ == "__main__":
    main()
