# Solidify to PRO — plan (before the next phase)

Goal: lock in everything built so far into a **professional, genuinely-correct,
real-life-useful** project — and make it **understandable** — before adding
anything new. No new features here; this is consolidation, correctness, and clarity.

## Where we are (one paragraph)
A Python "content engine" that reads the Quranic Arabic Corpus (1,473 verbs +
exact ayah refs), generates full conjugations, and **reconciles them against the
Quran** (attested = truth; generated = lower confidence; conflicts quarantined).
It also builds audio and packages a read-only `content.sqlite` two native apps
will load. 47 tests. ~81% of attested cells confirmed against the Quran.

## Workstreams (ordered)

### 1. Make it understandable (do this FIRST — for you & recruiters)
- A plain-language **WALKTHROUGH.md**: what the engine is, each pipeline stage,
  the correctness model (tiers), how to run it, what the bundle contains.
- A "read this project in 10 minutes" map. This is what you open to *get it*.

### 2. Consolidate into one clean tool
- Replace the ~8 `build_*.py` scripts with **one CLI**: `engine <stage>`
  (ingest / conjugate / reconcile / audio / cards / package / review / coverage /
  all). One obvious entry point; clean package layout; remove dead code.

### 3. Finish correctness to "trustworthy to ship"
- Last normalization pass (hamza-seat, split dual masc/fem) → target ~90% agreement.
- **Ship-safety rule:** every conjugation cell carries `source` + `confidence`;
  the app treats only `attested`/`consensus` as authoritative and **hides or
  clearly marks** anything uncertain. So even at 90%, we NEVER present a wrong
  form as fact. This is the real guarantee — not the percentage.
- Present vowel for the ~518 skipped Form-I verbs: small lexicon OR teach them
  only in their attested tenses. Decide.

### 4. Produce a REAL, usable bundle (not a toy)
- Full `content.sqlite` for a solid, real subset — e.g. the **top ~100 most
  frequent verbs**, each with: verified conjugation (attested/consensus only),
  meaning (en + bs), audio, and its exact ayah(s). A genuinely useful learning
  dataset an app can load as-is.
- Audio: decide the release path (macOS voice is a placeholder — not shippable).

### 5. Pro hardening
- CI (GitHub Actions) running the tests; one-command reproducible build with the
  QA + integrity gates; a **quality report** artifact ("N verbs, X% Quran-confirmed").
- Lint/type-check; consistent naming; delete scratch/demo scripts.

### 6. Version control
- The project is **not under git yet**. Init (personal identity, gmail; .gitignore
  already set), first commit. Push only on your OK.

## Definition of "PRO / done"
- [ ] A walkthrough you can read and understand the whole thing.
- [ ] One clean CLI; no dead scripts; clean structure.
- [ ] ~90% Quran-agreement AND a bundle that never ships an unverified form as fact.
- [ ] A real `content.sqlite` (top ~100 verbs) with audio + glosses + ayahs, app-ready.
- [ ] Tests + CI green; reproducible build; quality report.
- [ ] Under git.

When every box is checked, the project is "pro, real, useful" — then we plan the
next phase (native app skeleton / scaling / more languages).
