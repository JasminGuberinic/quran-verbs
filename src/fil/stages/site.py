"""Build the static study site: every verb in data/meanings.json, ready to learn from.

    fil site    →  build/site/{index.html, data.json, audio/…}

The site is a folder of plain files, so it opens locally and can be hosted anywhere for
free. What a learner sees is decided by the service and fil.study; this stage gathers it,
places the recitation clips beside the page, and refuses to ship what must not ship:

  - a verb without a meaning in every promised language (fil.meanings fails the load);
  - a sentence that failed the gate or that a reader refused (only shippable tiers go);
  - a "recitation" that is not audio (fil.recitation fails the download).

Anything not recited from the Quran is spoken by the viewer's own browser voice, so no
synthetic audio is distributed.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from fil import example_store, meanings, service, study
from fil.corpus.parse import iter_segments
from fil.examples import Example
from fil.languages import LANGUAGES
from fil.recitation import RecitationLibrary
from fil.resources import QAC_MORPHOLOGY, SITE_DIR
from fil.study import AyahExample, Location, QuranWord

_TEMPLATE = Path(__file__).resolve().parents[1] / "site" / "index.html"

# The forms a card leads with: he did, he does, and the command (only if the Quran has it —
# a generated "do wrong!" is not something to drill).
_PRINCIPAL = (("past", "huwa"), ("present", "huwa"), ("imperative", "anta"))

# Uthmani orthography marks a browser voice would stumble over; the page shows the
# Quranic spelling and speaks the standard one.
_UTHMANI_MARKS = "ۣۜ۟۠ۡۢۤۥۦۧۨ۩ٰ۪ۭ۫۬ٓ"


@dataclass(frozen=True)
class _Corpus:
    ayat: dict[tuple[int, int], tuple[QuranWord, ...]]
    standalone: dict[str, Location]
    nouns: dict[study.VerbKey, dict[str, study.DerivedNoun]]


def main(site: Path = SITE_DIR) -> None:
    studied = meanings.load()
    if not studied:
        print("data/meanings.json lists no verbs — nothing to build.")
        return

    corpus = _read_corpus()
    library = RecitationLibrary(site)
    _reset(site)
    catalogue = service.list_verbs()
    total = sum(verb.occurrence_count for verb in catalogue)
    ranks = {(verb.root, verb.form): rank for rank, verb in enumerate(catalogue, 1)}
    summaries = {(verb.root, verb.form): verb for verb in catalogue}

    verbs = [
        _verb_view(meaning, summaries[(meaning.root, meaning.form)],
                   ranks[(meaning.root, meaning.form)], total, corpus, library)
        for meaning in studied
    ]
    payload = {
        "totalOccurrences": total,
        "verbCount": len(catalogue),
        "languages": [
            {"code": language.code, "name": language.name, "rtl": language.is_rtl,
             "trust": language.trust}
            for language in LANGUAGES
        ],
        "verbs": verbs,
    }
    (site / "data.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    shutil.copyfile(_TEMPLATE, site / "index.html")
    _report(site, verbs)


def _read_corpus() -> _Corpus:
    with QAC_MORPHOLOGY.open(encoding="utf-8") as lines:
        segments = list(iter_segments(lines))
    words = study.words_of(segments)
    return _Corpus(study.ayat_of(words), study.standalone_locations(words), study.derived_nouns(segments))


def _reset(site: Path) -> None:
    """Start from an empty folder, so a clip dropped from the data is dropped from the site."""
    shutil.rmtree(site, ignore_errors=True)
    site.mkdir(parents=True)


def _verb_view(meaning, summary, rank: int, total: int, corpus: _Corpus,
               library: RecitationLibrary) -> dict:
    detail = service.get_verb(meaning.root, meaning.form)
    verb = (meaning.root, meaning.form)
    cells = [_cell_view(cell) for cell in detail.cells]
    return {
        "rank": rank, "root": detail.root, "form": detail.form, "lemma": detail.lemma,
        "count": summary.occurrence_count, "ayahCount": summary.ayah_count,
        "share": round(summary.occurrence_count / total * 100, 2),
        "meaning": dict(meaning.glosses),
        "principal": _principal(cells, corpus.standalone, library),
        "nouns": {kind: {"lemma": noun.lemma, "count": noun.count, "speak": _speakable(noun.lemma)}
                  for kind, noun in corpus.nouns.get(verb, {}).items()},
        "cells": cells,
        "ayat": [_ayah_view(example, verb, library) for example in study.example_ayat(corpus.ayat, verb)],
        "sentences": [
            _sentence_view(example)
            for example in example_store.load(meaning.root, meaning.form) if example.is_shippable
        ],
    }


def _cell_view(cell) -> dict:
    plain = cell.generated_form or cell.arabic
    return {"tense": cell.tense, "pronoun": cell.pronoun, "arabic": cell.arabic,
            "plain": plain, "speak": _speakable(plain), "quran": cell.source == "attested"}


def _principal(cells: list[dict], standalone: dict[str, Location], library: RecitationLibrary) -> list[dict]:
    by_cell = {(cell["tense"], cell["pronoun"]): cell for cell in cells}
    chosen = [
        by_cell[key] for key in _PRINCIPAL
        if key in by_cell and (key[0] != "imperative" or by_cell[key]["quran"])
    ]
    return [{**cell, "recited": _recited(cell, standalone, library)} for cell in chosen]


def _recited(cell: dict, standalone: dict[str, Location], library: RecitationLibrary) -> str | None:
    """The form as recited, when the Quran has it as a whole word — else None (browser voice)."""
    if not cell["quran"] or cell["arabic"] not in standalone:
        return None
    return library.word(*standalone[cell["arabic"]])


def _ayah_view(example: AyahExample, verb: study.VerbKey, library: RecitationLibrary) -> dict:
    return {
        "ref": example.ref,
        "tense": example.tense,
        "audio": library.ayah(example.surah, example.ayah),
        "words": [
            {"text": word.text, "hit": word.carries(verb),
             "audio": library.word(*word.location) if word.carries(verb) else None}
            for word in example.words
        ],
    }


def _sentence_view(example: Example) -> dict:
    return {
        "arabic": example.arabic,
        "speak": _speakable(example.arabic),
        "tense": example.tense, "pronoun": example.pronoun,
        "translation": {"bs": example.bs, "en": example.en, **dict(example.translations)},
        "independentlyReviewed": example.independently_reviewed,
        "words": [
            {"arabic": word.arabic, "target": word.is_target,
             "translation": {"bs": word.bs, "en": word.en, **dict(word.translations)}}
            for word in example.words
        ],
    }


def _speakable(text: str) -> str:
    return "".join(char for char in text if char not in _UTHMANI_MARKS).replace("ٱ", "ا")


def _report(site: Path, verbs: list[dict]) -> None:
    clips = sum(1 for _ in (site / "audio").rglob("*.mp3")) if (site / "audio").exists() else 0
    sentences = sum(len(verb["sentences"]) for verb in verbs)
    print(f"Wrote {site}")
    print(f"  verbs: {len(verbs)}  sentences: {sentences}  recitation clips: {clips}")
    thin = [verb["lemma"] for verb in verbs if len(verb["sentences"]) < 5]
    if thin:
        print(f"  fewer than 5 sentences: {' '.join(thin)}")
