# Fiʿl — learn every Quranic verb & its conjugation

A free, offline app that teaches the verbs of the Quran and their full
conjugation: see the root and form, hear high-quality audio, and practice.
Meanings are shown in the learner's language (**Bosnian and English** to start —
you learn Arabic *from* your language).

**Two native apps, one shared content bundle.** We ship **native iOS (SwiftUI)**
and **native Android (Kotlin/Compose)** — native for the best technical quality —
but both load the exact same platform-agnostic content bundle (`content.sqlite` +
audio + cards) produced by the pipeline below. All the hard work lives in the
pipeline, once.

**Design principle — a repeatable system, not a fixed list.** Adding a verb to
everything is one edit + one command; every verb flows through the same pipeline.
We prove the system on 1–2 verbs, then scale to all ~1,475.

## Two parts

### 1. Content pipeline (`pipeline/`, Python — build-time)
Turns hand-authored verbs into ready-to-bundle assets. Each stage is a Lego brick:

| Stage | Status | What it does |
|-------|--------|--------------|
| author | ✅ | `data/verbs.yaml` — the one human input (root, form, meaning, present vowel) |
| conjugate | ✅ | `conjugation.py` — full vocalized table via Qutrub (past/present/imperative × pronouns) |
| ayah-join | ⬜ | attach exact `surah:ayah` refs from the Quranic Arabic Corpus (never hand-typed) |
| audio | ⬜ | pluggable voice provider → per-form clips; ffmpeg trim + EBU R128 loudnorm → AAC |
| audio-QA | ⬜ | re-measure loudness/true-peak, silence/glitch + wrong-word checks |
| cards | ⬜ | deterministic typographic root/form cards (Amiri / Uthmani font) |
| package | ⬜ | bundle a read-only SQLite (+ SHA-256 integrity gate) for the app |

Run the whole thing with one command: `python pipeline/build_all.py`
(dataset → audio + QA → `content.sqlite` + integrity gate).

### 2. Native apps (planned) — both consume the same bundle
- **iOS** (`ios/`, SwiftUI + GRDB + AVAudioEngine)
- **Android** (`android/`, Kotlin + Jetpack Compose + Room/SQLite + ExoPlayer)

Each is offline, loads the bundled `content.sqlite` + audio, uses SM-2 spaced
repetition, and shows glosses in the user's chosen language. Same "Lego-brick"
components on both: an Arabic glyph view, an audio button, a conjugation table,
a card, and a practice interaction. Native (not cross-platform) for the best
tashkīl rendering and audio quality — the parts that matter most here.

## Decisions
- **Audio:** MVP uses a free voice provider + strict QA; upgrade to a human
  reciter (full buyout) for release quality. Tashkīl authored by hand, never auto.
- **Data:** open-source app → free to use the Quranic Arabic Corpus (GPL).
- **Images:** typographic/calligraphic cards (not illustrations of abstract verbs).
- **No ads.** Free to users; App Store publishing needs Apple's $99/yr (only for
  public release — building & on-device testing is free).

See `../project-ideas/QURAN-VERBS-APP-PLAN.md` for the full research-backed plan.
