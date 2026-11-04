"""Build the static study site: every verb in data/meanings.json, ready to learn from.

    fil site    →  build/site/{index.html, data.json, verbs/NNNN.json, ayat/NNNN[.lang].json}

The site is a folder of plain files, so it opens locally and can be hosted anywhere for
free. data.json is a light index; each verb's card, with its sound embedded, is its own
file, loaded when the learner reaches it — one file per verb, not hundreds of clips.
A card lists every form the Quran uses its verb in; the ayat themselves (every one, with
its free translation) wait in ayat/, fetched only when asked for. No ayah recitation is
ever shipped: every ayah, on a card or in a list, streams from the reciter's source
(fil.recitation) when it is played.
Where the sound goes is a strategy (fil.site_audio): embedded here, separate shared files
for the public site (fil pages), which assembles the very same cards through `assemble`.

What a learner sees is decided by the service, fil.study and fil.speech; this stage gathers
it and refuses to ship what must not ship:

  - a verb without a meaning in every promised language (fil.meanings fails the load);
  - a sentence that failed the gate or that a reader refused (only shippable tiers go);
  - a "recitation" that is not audio (fil.recitation fails the build).

Two kinds of sound, never confused: human recitation of the Quran (whole ayat, streamed,
and each form wherever the Quran recites it, from QuranHive's word-by-word clips), and synthetic speech for everything — every cell,
noun and practice sentence — spoken from a reading checked against a second, independent
reader (fil.speech). Where the two readers disagree, the build says so.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from fil import attested_forms, example_store, meanings, service, study
from fil.attested_forms import FormOccurrence, Grammar, VerbAyah
from fil.audio import RECITATION_BITRATE, compact_aac_command, compact_clip_name
from fil.ayah_translations import AyahTranslations
from fil.corpus.parse import iter_segments
from fil.examples import Example
from fil.languages import CODES, LANGUAGES, only_active
from fil.quran_numbering import ayah_number
from fil.recitation import AYAH_STREAM, QuranHiveArchive, RecitationMissing, WordRecitations, ayah_stream
from fil.resources import (AYAH_VERB_GLOSSES_JSON, BUILD_DIR, QAC_MORPHOLOGY, QURANHIVE_WORD_AUDIO, RECITATION_CACHE,
                           SITE_DIR, SPEECH_CACHE)
from fil.site_audio import AudioSink, EmbeddedAudio
from fil.speech import SpeechLibrary, TtsArabicVoice
from fil.stages import forms
from fil.study import AyahExample, QuranWord
from fil.word_translations import NoWordTranslations, WordTranslations

_TEMPLATE = Path(__file__).resolve().parents[1] / "site" / "index.html"
APP_FILES = ("index.html", "ui.js", "practice.js", "ayat.js", "player.js")
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
    uses: dict[study.VerbKey, tuple[FormOccurrence, ...]]


@dataclass(frozen=True)
class SiteContent:
    """Everything the app shows: the index (data.json) and one card per studied verb."""
    payload: dict
    cards: tuple[dict, ...]
    speech: SpeechLibrary
    missing_recitations: tuple[str, ...] = ()    # word locations the reciter's source lacks
    ayat_lists: tuple[tuple[str, dict], ...] = ()  # (path, content): every verb's full ayat, fetched on demand


class _Sound:
    """Turns a recitation or a spoken text into a reference the page can play."""

    def __init__(self, sink: AudioSink, recitations: WordRecitations | None = None,
                 word_translations: WordTranslations | None = None) -> None:
        self.sink = sink
        self.recitations = recitations or WordRecitations(QuranHiveArchive(QURANHIVE_WORD_AUDIO),
                                                          RECITATION_CACHE / "quranhive")
        self.missing_words: list[str] = []
        self.speech = SpeechLibrary(TtsArabicVoice(), SPEECH_CACHE)
        self.translations = AyahTranslations()
        self.verb_glosses = _verb_glosses()
        self.form_glosses = forms.read_glosses()[0]
        # No word-by-word source is wired yet: forms without our own gloss show their grammar.
        self.word_translations = word_translations or NoWordTranslations()

    @staticmethod
    def ayah(surah: int, ayah: int) -> str:
        """An ayah's recitation is streamed from its source, never shipped."""
        return ayah_stream(surah, ayah)

    def word(self, surah: int, ayah: int, word: int) -> str | None:
        """A word's recitation, or None (noted for the report) when the source has no clip for it."""
        try:
            clip = self.recitations.word(surah, ayah, word)
        except RecitationMissing:
            self.missing_words.append(f"{surah}:{ayah}:{word}")
            return None
        return self._recited(clip)

    def spoken(self, text: str) -> str:
        return self.sink.reference(self.speech.clip(text))

    def _recited(self, clip: Path) -> str:
        """Word clips arrive as stereo 64 kb/s MP3s; ship them as compact mono AAC."""
        compact = _COMPRESSED / compact_clip_name(f"quranhive/{clip.name}", RECITATION_BITRATE)
        if not compact.exists():
            compact.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(compact_aac_command(clip, compact, RECITATION_BITRATE),
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

    cards, ayat_lists = [], []
    for meaning in studied:
        key = (meaning.root, meaning.form)
        card = _verb_view(meaning, summaries[key], ranks[key], total, corpus, sound)
        cards.append(card)
        ayat_lists.extend(_ayat_lists(card, attested_forms.verb_ayat(corpus.uses[key]), corpus, sound))
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
        "ayahAudio": AYAH_STREAM,
    }
    return SiteContent(payload, tuple(cards), sound.speech, tuple(sound.missing_words), tuple(ayat_lists))


def card_file(card: dict) -> str:
    return f"verbs/{card['rank']:04d}.json"


def ayat_file(rank: int, language: str | None = None) -> str:
    """A verb's full ayat list (Arabic), or their translation into one language."""
    return f"ayat/{rank:04d}{f'.{language}' if language else ''}.json"


def write_app(site: Path, content: SiteContent) -> None:
    """The app itself: its index, one card file per verb, and the page with its scripts."""
    for card in content.cards:
        (site / card_file(card)).write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
    for path, listed in content.ayat_lists:
        (site / path).write_text(json.dumps(listed, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (site / "data.json").write_text(json.dumps(content.payload, ensure_ascii=False), encoding="utf-8")
    for name in APP_FILES:
        shutil.copyfile(_TEMPLATE.parent / name, site / name)


def _read_corpus() -> _Corpus:
    with QAC_MORPHOLOGY.open(encoding="utf-8") as lines:
        segments = list(iter_segments(lines))
    words = study.words_of(segments, service.corpus_corrections())
    return _Corpus(study.ayat_of(words), study.recitation_index(words), study.derived_nouns(segments),
                   service.form_occurrences())


def reset(site: Path) -> None:
    """Start from an empty folder, so a verb dropped from the data is dropped from the site."""
    shutil.rmtree(site, ignore_errors=True)
    (site / "verbs").mkdir(parents=True)
    (site / "ayat").mkdir()


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
        "ayat": _example_ayat_view(verb, corpus, sound),
        "forms": _forms_view(verb, corpus.uses[verb], summary.occurrence_count, sound),
        "ayatFile": ayat_file(rank),
        "ayatTranslations": {language: ayat_file(rank, language) for language in sound.translations.languages
                             if language in CODES},
        "sentences": [
            _sentence_view(example, sound)
            for example in example_store.load(meaning.root, meaning.form) if example.is_shippable
        ],
    }


class FormsDoNotAddUp(ValueError):
    """The forms listed for a verb do not account for every time the Quran uses it."""


def _forms_view(verb: study.VerbKey, uses: tuple[FormOccurrence, ...], count: int, sound: _Sound) -> list[dict]:
    """Every word the Quran uses the verb in, the most frequent first, with its gloss if it has one."""
    forms = attested_forms.attested_forms(uses)
    if sum(form.count for form in forms) != count:
        raise FormsDoNotAddUp(f"{verb}: forms count {sum(form.count for form in forms)}, the verb {count}")
    return [_form_view(verb, form, sound) for form in forms]


def _form_view(verb: study.VerbKey, form: attested_forms.AttestedForm, sound: _Sound) -> dict:
    """A form's row: its word, recited as at its first occurrence, and what it means.

    Optional keys are left out when empty — one row per form on every page adds up.
    """
    surah, ayah, _word = form.first
    view = {"arabic": form.text, "count": form.count, "first": f"{surah}:{ayah}",
            "audio": sound.word(*form.first),
            "grammar": [attested_forms.grammar_view(grammar) for grammar in form.grammars]}
    meanings = {"gloss": only_active(attested_forms.gloss_of(verb, form, sound.form_glosses, sound.verb_glosses)),
                "wordTranslation": only_active(sound.word_translations.of(form.first))}
    return {**view, **{key: meaning for key, meaning in meanings.items() if meaning}}


def _ayat_lists(card: dict, ayat: list[VerbAyah], corpus: _Corpus, sound: _Sound) -> list[tuple[str, dict]]:
    """The verb's full ayat list and its translations, one file per language, fetched only when asked for."""
    arabic = {"ayat": [_listed_ayah(ayah, corpus.ayat[(ayah.surah, ayah.ayah)]) for ayah in ayat]}
    translated = {path: _translated_list(ayat, language, sound) for language, path in card["ayatTranslations"].items()}
    return [(card["ayatFile"], arabic), *translated.items()]


def _listed_ayah(ayah: VerbAyah, words: tuple[QuranWord, ...]) -> dict:
    # "number" addresses the ayah's streamed recitation (site/ayat.js fills AYAH_STREAM with it).
    return {"ref": ayah.ref, "number": ayah_number(ayah.surah, ayah.ayah),
            "text": " ".join(word.text for word in words),
            "hits": [index for index, word in enumerate(words) if word.number in ayah.words]}


def _translated_list(ayat: list[VerbAyah], language: str, sound: _Sound) -> dict:
    found = {ayah.ref: sound.translations.of(ayah.surah, ayah.ayah).get(language) for ayah in ayat}
    return {"by": sound.translations.credit(language),
            "text": {ref: translation["text"] for ref, translation in found.items() if translation}}


def _cell_view(cell, recitations: dict[str, study.Recitation], sound: _Sound) -> dict:
    """One conjugation cell: spoken, and recited too where the Quran recites it.

    A cell Arabic does not use is shown, marked "not used" — but never spoken: a voice
    reading it aloud would teach it like any other form.
    """
    plain = cell.plain
    recitation = recitations.get(cell.arabic) if cell.source == "attested" else None
    recited = sound.word(*recitation.location) if recitation else None
    return {
        "tense": cell.tense, "pronoun": cell.pronoun, "arabic": cell.arabic,
        "plain": plain, "quran": cell.source == "attested",
        "notUsed": not cell.is_used,
        "spoken": sound.spoken(plain) if cell.is_used else None,
        "recited": recited,
        "recitedText": recitation.text if recited else None,
    }


def _principal(cells: list[dict]) -> list[dict]:
    """The forms a card is shown by; a verb the Quran never uses in a principal cell
    (يَحْزَنُونَ, تَحْزَنُونَ only) is shown by the forms it does use, never by none — and
    never by a form Arabic does not use (the past of وَذَرَ)."""
    used = [cell for cell in cells if not cell["notUsed"]]
    by_cell = {(cell["tense"], cell["pronoun"]): cell for cell in used}
    principal = [
        by_cell[key] for key in _PRINCIPAL
        if key in by_cell and (key[0] != "imperative" or by_cell[key]["quran"])
    ]
    return principal or [cell for cell in used if cell["quran"]] or used


def _example_ayat_view(verb: study.VerbKey, corpus: _Corpus, sound: _Sound) -> list[dict]:
    uses = corpus.uses[verb]
    forms = attested_forms.forms_by_location(attested_forms.attested_forms(uses))
    readings = _readings_by_location(uses)
    return [_ayah_view(example, verb, forms, readings, sound) for example in study.example_ayat(corpus.ayat, verb, uses)]


def _readings_by_location(uses: tuple[FormOccurrence, ...]) -> dict[study.Location, list[dict]]:
    readings: dict[study.Location, list[dict]] = {}
    for use in uses:
        readings.setdefault(use.location, []).append(attested_forms.grammar_view(use.grammar))
    return readings


def _ayah_view(example: AyahExample, verb: study.VerbKey, forms: dict[study.Location, attested_forms.AttestedForm],
               readings: dict[study.Location, list[dict]], sound: _Sound) -> dict:
    """An example ayah; its verb shows its gloss, or — until it is glossed — its grammar, which is never wrong."""
    return {
        "ref": example.ref,
        "tense": example.tense,
        "category": attested_forms.grammar_view(Grammar(example.tense, example.pronoun, is_passive=False, objects=())),
        "audio": sound.ayah(example.surah, example.ayah),
        "translation": only_active(sound.translations.of(example.surah, example.ayah)),
        "words": [_ayah_word_view(word, verb, forms, readings, sound) for word in example.words],
    }


def _ayah_word_view(word: QuranWord, verb: study.VerbKey, forms: dict[study.Location, attested_forms.AttestedForm],
                    readings: dict[study.Location, list[dict]], sound: _Sound) -> dict:
    if not word.carries(verb):
        return {"text": word.text, "hit": False, "audio": None, "gloss": None}
    gloss = attested_forms.example_gloss(verb, word.location, forms, sound.form_glosses, sound.verb_glosses)
    view = {"text": word.text, "hit": True, "audio": sound.word(*word.location)}
    if attested_forms.is_complete(gloss):
        return {**view, "gloss": only_active(gloss)}
    return {**view, "gloss": None, "grammar": readings[word.location]}


def _verb_glosses() -> dict[str, dict[str, str]]:
    entries = json.loads(AYAH_VERB_GLOSSES_JSON.read_text(encoding="utf-8"))
    return {key: glosses for key, glosses in entries.items() if not key.startswith("_")}


def _sentence_view(example: Example, sound: _Sound | None = None) -> dict:
    return {
        "arabic": example.arabic,
        "spoken": sound.spoken(example.arabic) if sound else None,
        "tense": example.tense, "pronoun": example.pronoun,
        "translation": only_active({"bs": example.bs, "en": example.en, **dict(example.translations)}),
        "independentlyReviewed": example.independently_reviewed,
        "words": [
            {"arabic": word.arabic, "target": word.is_target,
             "translation": only_active({"bs": word.bs, "en": word.en, **dict(word.translations)})}
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
