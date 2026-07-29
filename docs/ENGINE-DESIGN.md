# The Content Engine — design

Plan only. The engine is the heart of the project: a **correctness-maximizing
content compiler** that turns raw sources into a complete, verified, app-ready
bundle. The native apps compute **nothing** — they read.

## Two hard constraints that shape everything

1. **The app leaves nothing to compute.** Every conjugated form (vocalized),
   its audio, its typographic card, the ayah text + references, glosses per
   language, search indexes, and spaced-repetition metadata are **precomputed**
   and packaged. The app is a thin reader over SQLite + media files.

2. **There may be no human Arabic checker.** So correctness cannot rest on one
   tool's output. It must come from **converging authoritative sources +
   automated verification**, with every cell carrying a **confidence** and a
   **provenance**. What we cannot verify to a high bar, we do not silently ship.

## Correctness strategy (the core — because we may lack a human reviewer)

A tiered oracle. For every conjugation cell:

- **Tier 1 — Attested (ground truth).** If the form occurs in the Quran, the
  **Quranic Arabic Corpus (QAC)** surface form is authoritative. These are also
  exactly the forms a learner meets — highest value and highest certainty.
- **Tier 2 — Consensus.** Otherwise, generate with **≥2 independent engines**
  (Qutrub + CAMeL Tools, optionally ElixirFM). Ship only if they **agree** and
  the vocalization validator passes.
- **Tier 3 — Single-source / disagreement → quarantine.** Anything only one
  engine produces, or where engines disagree, is **flagged, not shipped as
  fact** — routed to a small review queue and hidden or clearly marked in-app.

Consequences we turn into features:
- The app can show **"attested in the Quran"** badges and a confidence signal —
  honesty becomes a feature, and a scholar (if one ever appears) reviews only the
  small **quarantine set**, not 40,000 cells.
- **Automated audio verification:** an Arabic **ASR pass (Whisper)** must
  transcribe each clip back to the intended word — the machine checks the audio
  says the right thing, since we can't assume a human will.
- **Orthography separation:** Quran ayah text is Uthmani (from Tanzil/KFGQPC);
  generated drill forms are imlāʾī. They live in **separate fields and render
  paths** — generated text is never presented as Quran text.

## Pipeline — a staged DAG (pure transforms, I/O at the edges)

Each stage is reproducible, content-hash cached, and fail-fast. Pure decision
logic is separated from I/O so it is unit-testable without the heavy tools.

1. **Ingest** — parse QAC (+ MASAQ cross-check): every verb → root, form (I–X),
   morphology, attested forms, exact ayah refs. Backbone **and** oracle.
2. **Normalize** — Unicode NFC, Buckwalter→Arabic, orthography tagging
   (Uthmani vs imlāʾī), diacritic-order canonicalization.
3. **Generate** — full paradigms from ≥2 engines (Qutrub, CAMeL Tools).
4. **Reconcile** — apply the tiered oracle above; attach `source ∈
   {attested, consensus, quarantined}` + `confidence` to every cell; run the
   full-vocalization validator.
5. **Glosses** — English from QAC/dictionary; Bosnian via MT + light review;
   extensible per language.
6. **Audio** — pluggable voice provider (TTS for MVP, reciter for release) →
   ffmpeg trim + deterministic peak-normalize → AAC; then the **QA + ASR
   verification gate**.
7. **Cards** — deterministic typographic root/form cards (headless Chromium +
   Amiri/Scheherazade New; Uthmani only for ayah excerpts).
8. **Package** — one read-only SQLite (verbs, glosses, conjugations w/ source +
   confidence, ayat, audio w/ sha + duration, cards) + SHA-256 referential
   integrity gate + a **coverage/quality report** (how many cells attested vs
   consensus vs quarantined).
9. **Review export** — dump the quarantine set as a review sheet, so *if* a
   checker appears they touch only what's uncertain.

## Best-of-Python toolbox (max leverage)

| Concern | Tools |
|---|---|
| Morphology / conjugation | Qutrub (libqutrub), **CAMeL Tools** (camel_morph MSA), ElixirFM (optional 3rd opinion) |
| QAC / data | custom parser over the open QAC morphology; **pandas** for bulk transforms; **pydantic** for schemas + fail-fast validation |
| Arabic text | **PyArabic** (diacritics/normalization), arabic-reshaper + python-bidi (rendering) |
| Audio processing | **ffmpeg** (via ffmpeg-python), **pyloudnorm** (LUFS), **soundfile/librosa** (analysis), ffmpeg-normalize |
| AI verification | **faster-whisper** (Arabic ASR to verify each clip says the right word); TTS: Azure ar-SA / Piper (MVP) |
| Cards | **Playwright** (headless Chromium, deterministic Arabic rendering) |
| Build / quality | content-hash caching, **pytest** (golden + differential + structural), CI |

## Code standard for the engine (modern, clean)

Per `CLAUDE.md`, and specifically: **prefer comprehensions / generators /
`itertools` / `map`/`filter` / small pure functions over nested `for` loops**
(e.g. iterate a paradigm with `itertools.product(tenses, pronouns)` instead of a
loop-in-a-loop) — but readability first (never nested comprehensions that hurt
clarity). Strategy/Adapter/Pipeline patterns for generators, voice providers,
and stages. Full type hints; frozen dataclasses; fail-fast.

## Built for extensibility (verbs now, more later)

Model the spine generically: a `MorphologicalItem` flowing through
ingest → generate → reconcile → audio → cards → package, with **pluggable
paradigm generators**. Verbs + their conjugations are the only concrete
implementation now; nouns (singular/plural/case), participles, etc. become new
generators on the same spine later — no re-architecture.

## Output contract (what the app reads — nothing to compute)

Read-only SQLite:
- `verbs(verb_id, root, form, dictionary_form, ayat_refs)`
- `verb_glosses(verb_id, lang, text)`
- `conjugations(verb_id, tense, pronoun, arabic, audio_file, audio_sha256, source, confidence)`
- `ayat(surah, ayah, uthmani_text)` + link table
- `cards(verb_id, image_file, image_sha256)`
- `meta(version, built_at, coverage_report)`

Everything keyed structurally so the app only does lookups + media playback.

## Phased build (when we implement — plan, not now)

1. QAC ingest + normalize (oracle + data source) — the foundation.
2. Multi-generator conjugation + reconciliation + confidence tiers.
3. Audio pipeline + Whisper ASR verification gate.
4. Cards.
5. Package + coverage/quality report + review export.
6. Scale to all verbs + CI + golden/differential test suite per verb class.

We keep and extend what already works (models/conjugation/audio/QA/packaging +
28 tests); this design is their generalization, not a rewrite.
