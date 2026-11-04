"""Build the static study site: every verb in data/meanings.json, ready to learn from.

    fil site    →  build/site/{index.html, data.json, verbs/NNNN.json}

The site is a folder of plain files, so it opens locally and can be hosted anywhere for
free. data.json is a light index; each verb's card, with its sound embedded, is its own
file, loaded when the learner reaches it — one file per verb, not hundreds of clips.
Where the sound goes is a strategy (fil.site_audio): embedded here, separate shared files
for the public site (fil pages), which assembles the very same cards through `assemble`.

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

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from fil import example_store, meanings, service, study
from fil.audio import RECITATION_BITRATE, compact_aac_command, compact_clip_name
from fil.ayah_translations import AyahTranslations
from fil.corpus.parse import iter_segments
from fil.examples import Example
from fil.languages import LANGUAGES, REQUIRED
from fil.recitation import RecitationLibrary, RecitationMissing
from fil.resources import AYAH_VERB_GLOSSES_JSON, BUILD_DIR, QAC_MORPHOLOGY, RECITATION_CACHE, SITE_DIR, SPEECH_CACHE
from fil.site_audio import AudioSink, EmbeddedAudio
from fil.speech import SpeechLibrary, TtsArabicVoice
from fil.study import AyahExample, QuranWord

_TEMPLATE = Path(__file__).resolve().parents[1] / "site" / "index.html"
APP_FILES = ("index.html", "ui.js", "practice.js")
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


@dataclass(frozen=True)
class SiteContent:
    """Everything the app shows: the index (data.json) and one card per studied verb."""
    payload: dict
    cards: tuple[dict, ...]
    speech: SpeechLibrary
    missing_recitations: tuple[str, ...] = ()    # word locations the reciter's source lacks


class _Sound:
    """Turns a recitation or a spoken text into a reference the page can play."""

    def __init__(self, sink: AudioSink, recitations: RecitationLibrary | None = None) -> None:
        self.sink = sink
        self.recitations = recitations or RecitationLibrary(BUILD_DIR / "recitation-stage", cache=RECITATION_CACHE)
        self.missing_words: list[str] = []
        self.speech = SpeechLibrary(TtsArabicVoice(), SPEECH_CACHE)
        self.translations = AyahTranslations()
        self.verb_glosses = _verb_glosses()

    def ayah(self, surah: int, ayah: int) -> str:
        return self._recited(self.recitations.ayah(surah, ayah))

    def word(self, surah: int, ayah: int, word: int) -> str | None:
        """A word's recitation, or None (noted for the report) when the source has no clip for it."""
        try:
            site_path = self.recitations.word(surah, ayah, word)
        except RecitationMissing:
            self.missing_words.append(f"{surah}:{ayah}:{word}")
            return None
        return self._recited(site_path)

    def spoken(self, text: str) -> str:
        return self.sink.reference(self.speech.clip(text))

    def _recited(self, site_path: str) -> str:
        """Recitations arrive as large MP3s (a single word is 320 kb/s); ship them compact."""
        source = RECITATION_CACHE / site_path
        compact = _COMPRESSED / compact_clip_name(site_path, RECITATION_BITRATE)
        if not compact.exists():
            compact.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(compact_aac_command(source, compact, RECITATION_BITRATE),
                           check=True, capture_output=True)
        return self.sink.reference(compact)


def main(site: Path = SITE_DIR) -> None:
    content = assemble(EmbeddedAudio())
    if content is None:
        return
    reset(site)
    write_app(site, content)
    report(site, content)


def assemble(sink: AudioSink) -> SiteContent | None:
    """Every studied verb's card, its sound handed to `sink`; None when nothing is studied."""
    studied = meanings.load()
    if not studied:
        print("data/meanings.json lists no verbs — nothing to build.")
        return None

    corpus = _read_corpus()
    sound = _Sound(sink)
    catalogue = service.list_verbs()
    total = sum(verb.occurrence_count for verb in catalogue)
    ranks = {(verb.root, verb.form): rank for rank, verb in enumerate(catalogue, 1)}
    summaries = {(verb.root, verb.form): verb for verb in catalogue}

    cards = []
    for meaning in studied:
        key = (meaning.root, meaning.form)
        card = _verb_view(meaning, summaries[key], ranks[key], total, corpus, sound)
        cards.append(card)
        print(f"  {card['rank']:>4} {card['lemma']}", flush=True)

    payload = {
        "totalOccurrences": total,
        "verbCount": len(catalogue),
        "languages": [
            {"code": language.code, "name": language.name, "rtl": language.is_rtl,
             "trust": language.trust}
            for language in LANGUAGES
        ],
        "verbs": [{**_summary_of(card), "file": card_file(card)} for card in cards],
    }
    return SiteContent(payload, tuple(cards), sound.speech, tuple(sound.missing_words))


def card_file(card: dict) -> str:
    return f"verbs/{card['rank']:04d}.json"


def write_app(site: Path, content: SiteContent) -> None:
    """The app itself: its index, one card file per verb, and the page with its scripts."""
    for card in content.cards:
        (site / card_file(card)).write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
    (site / "data.json").write_text(json.dumps(content.payload, ensure_ascii=False), encoding="utf-8")
    for name in APP_FILES:
        shutil.copyfile(_TEMPLATE.parent / name, site / name)


def _read_corpus() -> _Corpus:
    with QAC_MORPHOLOGY.open(encoding="utf-8") as lines:
        segments = list(iter_segments(lines))
    words = study.words_of(segments, service.corpus_corrections())
    return _Corpus(study.ayat_of(words), study.recitation_index(words), study.derived_nouns(segments))


def reset(site: Path) -> None:
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
    plain = cell.plain
    recitation = recitations.get(cell.arabic) if cell.source == "attested" else None
    recited = sound.word(*recitation.location) if recitation else None
    return {
        "tense": cell.tense, "pronoun": cell.pronoun, "arabic": cell.arabic,
        "plain": plain, "quran": cell.source == "attested",
        "spoken": sound.spoken(plain),
        "recited": recited,
        "recitedText": recitation.text if recited else None,
    }


def _principal(cells: list[dict]) -> list[dict]:
    """The forms a card is shown by; a verb the Quran never uses in a principal cell
    (يَحْزَنُونَ, تَحْزَنُونَ only) is shown by the forms it does use, never by none."""
    by_cell = {(cell["tense"], cell["pronoun"]): cell for cell in cells}
    principal = [
        by_cell[key] for key in _PRINCIPAL
        if key in by_cell and (key[0] != "imperative" or by_cell[key]["quran"])
    ]
    return principal or [cell for cell in cells if cell["quran"]] or cells


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
    if key not in glosses or not all(glosses[key].get(code) for code in REQUIRED):
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


def report(site: Path, content: SiteContent) -> None:
    cards, speech = content.cards, content.speech
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
    if content.missing_recitations:
        print(f"  no recited clip at the source (shown without one): {' '.join(content.missing_recitations)}")
    thin = [card["lemma"] for card in cards if len(card["sentences"]) < 5]
    if thin:
        print(f"  fewer than 5 sentences: {' '.join(thin)}")
