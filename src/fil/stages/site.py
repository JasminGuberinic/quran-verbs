"""Build the static study site: every verb in data/meanings.json, ready to learn from.

    fil site    →  build/site/{index.html, data.json, verbs/NNNN.json}

The site is a folder of plain files, so it opens locally and can be hosted anywhere for
free. data.json is a light index; each verb's card, with its sound embedded, is its own
file, loaded when the learner reaches it — one file per verb, not hundreds of clips.

What a learner sees is decided by the service, fil.study and fil.speech; this stage gathers
it and refuses to ship what must not ship:

  - a verb without a meaning in every promised language (fil.meanings fails the load);
  - a sentence that failed the gate or that a reader refused (only shippable tiers go);
  - a "recitation" that is not audio (fil.recitation fails the download).

Two kinds of sound, never confused: human recitation of the Quran (whole ayat, and each
form wherever the Quran recites it), and synthetic speech for everything — every cell,
noun and practice sentence — spoken from a reading checked against a second, independent
reader (fil.speech). Where the two readers disagree, the build says so.
"""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from fil import example_store, meanings, service, study
from fil.ayah_translations import AyahTranslations
from fil.corpus.parse import iter_segments
from fil.examples import Example
from fil.languages import LANGUAGES
from fil.recitation import RecitationLibrary
from fil.resources import AYAH_VERB_GLOSSES_JSON, BUILD_DIR, QAC_MORPHOLOGY, RECITATION_CACHE, SITE_DIR, SPEECH_CACHE
from fil.speech import SpeechLibrary, TtsArabicVoice
from fil.study import AyahExample, QuranWord

_TEMPLATE = Path(__file__).resolve().parents[1] / "site" / "index.html"
_COMPRESSED = BUILD_DIR / "compressed-cache"
_REVIEW = BUILD_DIR / "site-review.txt"

# The forms a card leads with: he did, he does, and the command (only if the Quran has it —
# a generated "do wrong!" is not something to drill).
_PRINCIPAL = (("past", "huwa"), ("present", "huwa"), ("imperative", "anta"))


@dataclass(frozen=True)
class _Corpus:
    ayat: dict[tuple[int, int], tuple[QuranWord, ...]]
    recitations: dict[str, study.Recitation]
    nouns: dict[study.VerbKey, dict[str, study.DerivedNoun]]


class _Sound:
    """Turns a recitation or a spoken text into an embeddable data URI."""

    def __init__(self) -> None:
        self.recitations = RecitationLibrary(BUILD_DIR / "recitation-stage", cache=RECITATION_CACHE)
        self.speech = SpeechLibrary(TtsArabicVoice(), SPEECH_CACHE)
        self.translations = AyahTranslations()
        self.verb_glosses = _verb_glosses()

    def ayah(self, surah: int, ayah: int) -> str:
        return self._recited(self.recitations.ayah(surah, ayah))

    def word(self, surah: int, ayah: int, word: int) -> str:
        return self._recited(self.recitations.word(surah, ayah, word))

    def spoken(self, text: str) -> str:
        return _data_uri(self.speech.clip(text))

    def _recited(self, site_path: str) -> str:
        """Recitations arrive as large MP3s (a single word is 320 kb/s); ship them compact."""
        source = RECITATION_CACHE / site_path
        compact = _COMPRESSED / f"{hashlib.sha1(site_path.encode()).hexdigest()}.m4a"
        if not compact.exists():
            compact.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", "64000",
                            str(source), str(compact)], check=True, capture_output=True)
        return _data_uri(compact)


def _data_uri(clip: Path) -> str:
    return "data:audio/mp4;base64," + base64.b64encode(clip.read_bytes()).decode()


def main(site: Path = SITE_DIR) -> None:
    studied = meanings.load()
    if not studied:
        print("data/meanings.json lists no verbs — nothing to build.")
        return

    corpus = _read_corpus()
    sound = _Sound()
    _reset(site)
    catalogue = service.list_verbs()
    total = sum(verb.occurrence_count for verb in catalogue)
    ranks = {(verb.root, verb.form): rank for rank, verb in enumerate(catalogue, 1)}
    summaries = {(verb.root, verb.form): verb for verb in catalogue}

    index = []
    for meaning in studied:
        key = (meaning.root, meaning.form)
        card = _verb_view(meaning, summaries[key], ranks[key], total, corpus, sound)
        name = f"verbs/{ranks[key]:04d}.json"
        (site / name).write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
        index.append({**_summary_of(card), "file": name})
        print(f"  {card['rank']:>4} {card['lemma']}", flush=True)

    payload = {
        "totalOccurrences": total,
        "verbCount": len(catalogue),
        "languages": [
            {"code": language.code, "name": language.name, "rtl": language.is_rtl,
             "trust": language.trust}
            for language in LANGUAGES
        ],
        "verbs": index,
    }
    (site / "data.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    shutil.copyfile(_TEMPLATE, site / "index.html")
    shutil.copyfile(_TEMPLATE.parent / "practice.js", site / "practice.js")
    _report(site, index, sound.speech)


def _read_corpus() -> _Corpus:
    with QAC_MORPHOLOGY.open(encoding="utf-8") as lines:
        segments = list(iter_segments(lines))
    words = study.words_of(segments)
    return _Corpus(study.ayat_of(words), study.recitation_index(words), study.derived_nouns(segments))


def _reset(site: Path) -> None:
    """Start from an empty folder, so a verb dropped from the data is dropped from the site."""
    shutil.rmtree(site, ignore_errors=True)
    (site / "verbs").mkdir(parents=True)


def _summary_of(card: dict) -> dict:
    """What the index needs to list a verb and count progress, without loading its card."""
    keys = ("rank", "root", "form", "lemma", "count", "ayahCount", "share", "meaning")
    return {key: card[key] for key in keys}


def _verb_view(meaning, summary, rank: int, total: int, corpus: _Corpus, sound: _Sound) -> dict:
    detail = service.get_verb(meaning.root, meaning.form)
    verb = (meaning.root, meaning.form)
    cells = [_cell_view(cell, corpus.recitations, sound) for cell in detail.cells]
    return {
        "rank": rank, "root": detail.root, "form": detail.form, "lemma": detail.lemma,
        "count": summary.occurrence_count, "ayahCount": summary.ayah_count,
        "share": round(summary.occurrence_count / total * 100, 2),
        "meaning": dict(meaning.glosses),
        "lemmaSpoken": sound.spoken(detail.lemma),
        "principal": _principal(cells),
        "nouns": {kind: {"lemma": noun.lemma, "count": noun.count, "spoken": sound.spoken(noun.lemma)}
                  for kind, noun in corpus.nouns.get(verb, {}).items()},
        "cells": cells,
        "ayat": [_ayah_view(example, verb, sound) for example in study.example_ayat(corpus.ayat, verb)],
        "sentences": [
            _sentence_view(example, sound)
            for example in example_store.load(meaning.root, meaning.form) if example.is_shippable
        ],
    }


def _cell_view(cell, recitations: dict[str, study.Recitation], sound: _Sound) -> dict:
    """One conjugation cell: always spoken, and recited too where the Quran recites it."""
    plain = cell.generated_form or cell.arabic
    recitation = recitations.get(cell.arabic) if cell.source == "attested" else None
    return {
        "tense": cell.tense, "pronoun": cell.pronoun, "arabic": cell.arabic,
        "plain": plain, "quran": cell.source == "attested",
        "spoken": sound.spoken(plain),
        "recited": sound.word(*recitation.location) if recitation else None,
        "recitedText": recitation.text if recitation else None,
    }


def _principal(cells: list[dict]) -> list[dict]:
    by_cell = {(cell["tense"], cell["pronoun"]): cell for cell in cells}
    return [
        by_cell[key] for key in _PRINCIPAL
        if key in by_cell and (key[0] != "imperative" or by_cell[key]["quran"])
    ]


def _ayah_view(example: AyahExample, verb: study.VerbKey, sound: _Sound) -> dict:
    return {
        "ref": example.ref,
        "tense": example.tense,
        "audio": sound.ayah(example.surah, example.ayah),
        "translation": sound.translations.of(example.surah, example.ayah),
        "words": [
            {"text": word.text, "hit": word.carries(verb),
             "audio": sound.word(*word.location) if word.carries(verb) else None,
             "gloss": _gloss_of(word, sound.verb_glosses) if word.carries(verb) else None}
            for word in example.words
        ],
    }


def _verb_glosses() -> dict[str, dict[str, str]]:
    entries = json.loads(AYAH_VERB_GLOSSES_JSON.read_text(encoding="utf-8"))
    return {key: glosses for key, glosses in entries.items() if not key.startswith("_")}


class MissingVerbGloss(ValueError):
    """An example ayah's verb has no in-context translation — the card would be half-empty."""


def _gloss_of(word: QuranWord, glosses: dict[str, dict[str, str]]) -> dict[str, str]:
    key = f"{word.surah}:{word.ayah}:{word.number}"
    if key not in glosses or not all(glosses[key].get(code) for code in (lang.code for lang in LANGUAGES)):
        raise MissingVerbGloss(f"{key} ({word.text}): add its translation to {AYAH_VERB_GLOSSES_JSON.name}")
    return glosses[key]


def _sentence_view(example: Example, sound: _Sound | None = None) -> dict:
    return {
        "arabic": example.arabic,
        "spoken": sound.spoken(example.arabic) if sound else None,
        "tense": example.tense, "pronoun": example.pronoun,
        "translation": {"bs": example.bs, "en": example.en, **dict(example.translations)},
        "independentlyReviewed": example.independently_reviewed,
        "words": [
            {"arabic": word.arabic, "target": word.is_target,
             "translation": {"bs": word.bs, "en": word.en, **dict(word.translations)}}
            for word in example.words
        ],
    }


def _report(site: Path, index: list[dict], speech: SpeechLibrary) -> None:
    cards = [json.loads((site / entry["file"]).read_text(encoding="utf-8")) for entry in index]
    sentences = sum(len(card["sentences"]) for card in cards)
    size = sum(path.stat().st_size for path in site.rglob("*") if path.is_file()) / 1e6
    disagreements = speech.disagreements
    print(f"Wrote {site}  ({size:.1f} MB)")
    print(f"  verbs: {len(cards)}  sentences: {sentences}  spoken texts: {len(speech.verdicts)}")
    print(f"  both readers agree on {len(speech.verdicts) - len(disagreements)}; "
          f"{len(disagreements)} spoken from our reading where the model's own differs "
          f"(listed in {_REVIEW.relative_to(BUILD_DIR.parent)})")
    _REVIEW.write_text("".join(
        f"{verdict.text}\n  ours:  {' '.join(verdict.expected)}\n  model: {' '.join(verdict.produced)}\n"
        for verdict in disagreements
    ), encoding="utf-8")
    thin = [card["lemma"] for card in cards if len(card["sentences"]) < 5]
    if thin:
        print(f"  fewer than 5 sentences: {' '.join(thin)}")
