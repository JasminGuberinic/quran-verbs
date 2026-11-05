"""The nouns and adjectives of the Quran (phase 3, docs/NOUNS-PLAN.md).

    fil nouns status            how many nouns, how cleanly their words come apart, their plurals
    fil nouns catalogue         build/nouns/catalogue.tsv (+ proper_names.tsv): every lemma by rank
    fil nouns paradigms [TOP]   build/nouns/paradigms.tsv: the case table of the TOP lemmas (default 600),
                                Quranic spellings first, CAMeL Tools for the rest, every form gated
    fil nouns pictures OPENMOJI_DIR TWEMOJI_DIR
                                assets/nouns/<slug>.svg: the chosen emoji of data/noun_pictures.json,
                                recoloured to our greens; fails if any picture fails the gate
    fil nouns picture-candidates OPENMOJI_DIR TWEMOJI_DIR
                                build/nouns/picture-candidates/{openmoji,twemoji}/: both sets' version
                                of every mapped noun, for the reviewer to choose from
    fil nouns batch …           add studied nouns in batches of 50 (fil.stages.noun_batch)

This stage is the composition root of the noun engine: it reads the corpus, loads our
verbs, and wires CAMeL in as the generator.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from fil import meanings
from fil.corpus.nouns import iter_noun_occurrences
from fil.corpus.parse import iter_segments
from fil.nouns.catalogue import TSV_COLUMNS, build_catalogue, tsv_rows
from fil.nouns.model import (ATTESTED, BROKEN, GENERATED, MISSING, PROPER_NOUN, SOUND_FEMININE, SOUND_MASCULINE,
                             NounLemma, NounOccurrence, Paradigm)
from fil.nouns.paradigm import NounGenerator, build_paradigm
from fil.noun_pictures import EmojiDirectory, EmojiNotFound, emoji_directories, load_pictures, write_pictures
from fil.nouns.pictures import shown
from fil.resources import BUILD_DIR, NOUN_PICTURES_DIR, QAC_MORPHOLOGY

OUT = BUILD_DIR / "nouns"
TOP = 600
REASONS_SHOWN = 4


# ---------------------------------------------------------------- commands

def status() -> None:
    occurrences = load_occurrences()
    lemmas = catalogue(occurrences)
    common = [lemma for lemma in lemmas if lemma.kind != PROPER_NOUN]
    print(f"nouns: {len(occurrences):,} occurrences of {len(lemmas):,} lemmas — {_kinds(lemmas)}")
    print(f"decomposed cleanly: {_clean_share(occurrences)}")
    print(f"plurals: {_plurals(common)}")
    top = common[:TOP]
    covered = sum(lemma.count for lemma in top) / sum(lemma.count for lemma in common)
    linked = sum(1 for lemma in top if lemma.linked_verb)
    print(f"top {TOP}: {covered:.0%} of non-name occurrences; {linked} linked to a verb we teach")


def write_catalogue() -> None:
    lemmas = catalogue(load_occurrences())
    common = [lemma for lemma in lemmas if lemma.kind != PROPER_NOUN]
    names = [lemma for lemma in lemmas if lemma.kind == PROPER_NOUN]
    _write_tsv(OUT / "catalogue.tsv", TSV_COLUMNS, tsv_rows(common))
    _write_tsv(OUT / "proper_names.tsv", TSV_COLUMNS, tsv_rows(names))
    print(f"nouns catalogue: {len(common):,} lemmas → {OUT / 'catalogue.tsv'}; {len(names)} names → proper_names.tsv")


def write_paradigms(top: int = TOP) -> None:
    from fil.camel_nouns import CamelNounGenerator   # heavy: only this command loads it

    occurrences = load_occurrences()
    lemmas = [lemma for lemma in catalogue(occurrences) if lemma.kind != PROPER_NOUN][:top]
    paradigms = build_paradigms(lemmas, occurrences, CamelNounGenerator())
    rows = [(lemma.lemma, found.cell.code, found.text or "", found.source, "; ".join(found.problems))
            for lemma, paradigm in zip(lemmas, paradigms) for found in paradigm.cells]
    _write_tsv(OUT / "paradigms.tsv", ("lemma", "cell", "arabic", "source", "problems"), rows)
    _report_paradigms(paradigms)


# ---------------------------------------------------------------- wiring

def load_occurrences() -> list[NounOccurrence]:
    with QAC_MORPHOLOGY.open(encoding="utf-8") as lines:
        return list(iter_noun_occurrences(iter_segments(lines)))


def catalogue(occurrences: Sequence[NounOccurrence]) -> tuple[NounLemma, ...]:
    taught = [f"{meaning.root}_{meaning.form}" for meaning in meanings.load()]
    return build_catalogue(occurrences, taught)


def write_noun_pictures(openmoji: Path, twemoji: Path) -> None:
    pictures = load_pictures()
    problems = write_pictures(shown(pictures), emoji_directories(openmoji, twemoji))
    if problems:
        print("\n".join(problems), file=sys.stderr)
        raise SystemExit(f"{len(problems)} picture problems: nothing that fails the gate ships")
    print(f"noun pictures: {len(shown(pictures))} of {len(pictures)} picturable nouns → {NOUN_PICTURES_DIR}")


def write_picture_candidates(openmoji: Path, twemoji: Path) -> None:
    directories = emoji_directories(openmoji, twemoji)
    mapped = [picture for picture in load_pictures() if picture.codepoint]
    for name, directory in directories.items():
        candidates = [replace(picture, source=directory.source) for picture in mapped]
        available = [picture for picture in candidates if _has_emoji(directory, picture.codepoint)]
        problems = write_pictures(available, {name: directory}, OUT / "picture-candidates" / name)
        print(f"{directory.source.title}: {len(available)} of {len(mapped)} candidates, {len(problems)} fail the gate")
        print("\n".join(problems[:10]))


def _has_emoji(directory: EmojiDirectory, codepoint: str) -> bool:
    try:
        directory.svg(codepoint)
    except EmojiNotFound:
        return False
    return True


def occurrences_by_lemma(occurrences: Sequence[NounOccurrence]) -> dict[tuple[str, str], list[NounOccurrence]]:
    by_lemma: dict[tuple[str, str], list[NounOccurrence]] = defaultdict(list)
    for occurrence in occurrences:
        by_lemma[(occurrence.lemma, occurrence.root)].append(occurrence)
    return by_lemma


def build_paradigms(lemmas: Sequence[NounLemma], occurrences: Sequence[NounOccurrence],
                    generator: NounGenerator) -> list[Paradigm]:
    by_lemma = occurrences_by_lemma(occurrences)
    return [build_paradigm(lemma, by_lemma[(lemma.lemma, lemma.root)], generator) for lemma in lemmas]


# ---------------------------------------------------------------- summaries

def _kinds(lemmas: Sequence[NounLemma]) -> str:
    counts = Counter(lemma.kind for lemma in lemmas)
    return ", ".join(f"{kind} {count}" for kind, count in counts.most_common())


def _clean_share(occurrences: Sequence[NounOccurrence]) -> str:
    clean = sum(1 for occurrence in occurrences if occurrence.is_clean)
    reasons = Counter(occurrence.skip_reason for occurrence in occurrences if not occurrence.is_clean)
    shown = ", ".join(f"{reason} {count}" for reason, count in reasons.most_common(REASONS_SHOWN))
    return f"{clean / len(occurrences):.1%} ({len(occurrences) - clean} not: {shown})"


def _plurals(lemmas: Sequence[NounLemma]) -> str:
    kinds = Counter(plural.kind for lemma in lemmas for plural in lemma.plurals)
    with_plural = sum(1 for lemma in lemmas if lemma.plurals)
    with_dual = sum(1 for lemma in lemmas if lemma.dual_count)
    return (f"{with_plural} lemmas have one in the Quran — patterns: sound m. {kinds[SOUND_MASCULINE]}, "
            f"sound f. {kinds[SOUND_FEMININE]}, broken {kinds[BROKEN]}; {with_dual} have a dual")


def _report_paradigms(paradigms: Sequence[Paradigm]) -> None:
    sources = Counter(found.source for paradigm in paradigms for found in paradigm.cells)
    refused = Counter(found.problems[0].split(":")[0] for paradigm in paradigms for found in paradigm.cells
                      if found.source == MISSING and found.problems)
    total = sum(sources.values())
    complete = sum(1 for paradigm in paradigms if not paradigm.count(MISSING))
    print(f"paradigms: {len(paradigms)} lemmas, {total:,} cells — attested {sources[ATTESTED]:,}, "
          f"generated+gated {sources[GENERATED]:,}, missing {sources[MISSING]:,}; {complete} tables complete")
    print("missing because: " + ", ".join(f"{reason} {count}" for reason, count in refused.most_common(6)))
    print(f"→ {OUT / 'paradigms.tsv'}")


def _write_tsv(path: Path, header: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["\t".join(header)] + ["\t".join(row) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _batch(argv: list[str]) -> None:
    from fil.stages import noun_batch   # it builds on this stage's wiring

    noun_batch.main(argv)


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[2:]
    commands = {
        "status": status,
        "catalogue": write_catalogue,
        "paradigms": lambda: write_paradigms(int(args[1]) if len(args) > 1 else TOP),
        "pictures": lambda: write_noun_pictures(Path(args[1]), Path(args[2])),
        "picture-candidates": lambda: write_picture_candidates(Path(args[1]), Path(args[2])),
        "batch": lambda: _batch(args[1:]),
    }
    needs_emoji_directories = args[:1] in (["pictures"], ["picture-candidates"]) and len(args) < 3
    if not args or args[0] not in commands or needs_emoji_directories:
        print(__doc__)
        raise SystemExit(2)
    commands[args[0]]()
