---
name: fil-batch
description: Add the next batch of 25 verbs to the Fiʿl study site, token-efficiently. Use when the user says "/fil-batch 26-50", "next batch", "dodaj još glagola", or asks to add verbs to the site.
---

# Add a batch of verbs (Arabic + English + Bosnian)

Goal: about 400 verbs (88% of verb occurrences in the Quran), 25 per batch, one batch per
conversation. Arabic quality is the point; every printed line costs tokens, so work from
the compact files and read only what a step needs.

## Rules
- Start a **new conversation** per batch. Don't re-read docs or code you don't need.
- Use `.venv/bin/fil batch …` only. It prints failures and one-line summaries; never `cat` large files.
- Only **bs + en** in a batch. The other 14 languages fall back to English until a bulk
  translation pass (see "Later" below).
- Don't make product decisions alone; ask the user (in Bosnian, briefly).
- Commit when the batch is done, then `git push` (branch study-site only; never main).

## Content policy (practice sentences)
There is **no human reviewer**: the strict blind reviewer agent (step 6) stands in for one,
and the site says reviews are by AI. Never park a job "for a human".
- **First-person forms only God speaks in the Quran** (the I/We of revealing, creating,
  forbidding, saving, gathering…) get a practice sentence in an **ordinary human sense** of
  the verb — never attributed to God, never Quranic wording: نَجَّيْنَا الطِّفْلَ مِنَ الْغَرَقِ,
  حَرَّمْنَا التَّدْخِينَ فِي الْبَيْتِ, رَضِيتُ بِالنَّتِيجَةِ, خَلَقْتُ جَوًّا هَادِئًا.
- A form that **truly cannot be used sensibly** (e.g. the command قَاتِلْ "fight!") is parked
  with reason `skipped by policy: <why>`
  (`service.record_outcome(key, agenda.PARKED, reason="skipped by policy: …")`). It keeps its
  table, audio and ayat, just no sentence.
- **No Quranic wording.** The site labels practice sentences "not from the Quran", so never
  reproduce an ayah's phrase (e.g. قَاتِلْ فِي سَبِيلِ اللَّهِ, 4:84).
- **No fighting commands** addressed to the learner.
- **No "؟"** in practice sentences.
- **Analyzer/lexicon gaps** get documented entries, never a loosened check:
  a cell with no spelling the gate can use (or a wrong generated one) → `data/conjugation_overrides.json`
  (spellings + why; a documented spelling is also what the table shows);
  a refused gloss → `data/gloss_exceptions.json` under the correct CAMeL root, or — when the
  analyzer reads the word only under a wrong root — under `"spelling:<word>"` (e.g. `spelling:تُبْ`),
  with `root` and `why`.
- **Cells Arabic does not use** (impersonal يَنْبَغِي's أَنْبَغِي/اِنْبَغِ, the command of a verb of
  state like اِخْفَ, of كَادَ or مَا زَالَ) are marked, not hidden: add `"unused": true` + `why` in
  `data/conjugation_overrides.json` under `tense:pronoun`, `tense:1st`, `tense:2nd` or `tense:*`.
  The site greys them with a note, never speaks them, and no sentence may be planned for them.
  Only mark what you are sure of — a rare but possible form is not "not used".
- To revive a parked job: `service.record_outcome(key, agenda.TODO, reason="un-parked: <why>")`.

## Steps
1. `fil batch plan FROM TO` → `build/batch/plan.tsv` (job, the form to write, cell),
   `todo-meanings.tsv`, `todo-ayah.tsv`. (Already run for 26–50.)
2. `fil batch wordbank` → `build/batch/wordbank.tsv`: words whose glosses already passed the
   gate. Build sentences from these first; check any new word with `service.lookup_word`.
3. Meanings: write `build/batch/meanings.tsv` (`root_form  en  bs`), then `fil batch meanings …`.
   English should use a word the CAMeL lexicon glosses (it is checked); Bosnian natural.
4. Ayah verbs: write `build/batch/ayah.tsv` (`s:a:w  en  bs`) — the verb *as it stands in that
   ayah*, with its clitics and object pronouns — then `fil batch ayah …`.
5. Sentences: write `build/batch/draft-N.tsv`, one per line:
   `job<TAB>arabic words, target marked *<TAB>en<TAB>bs<TAB>en glosses|…<TAB>bs glosses|…`
   Short (2–4 words), natural MSA, full harakat, standard spelling (not Uthmani). Use the
   plan's form for the verb. Never put invented words in God's mouth; God-only first-person
   forms get an ordinary human sense (see Content policy).
   **Check first, then draft:** `fil batch check build/batch/draft-N.tsv` runs the same gate
   but records nothing (FAIL lines + a summary); fix until it is clean, then
   `fil batch draft build/batch/draft-N.tsv` — a failed draft spends one of the job's 3 attempts.
6. Blind review: `fil batch review-export`, then one general-purpose agent (strong model)
   reads `build/batch/blind.json` and writes verdicts JSON (same prompt shape as before:
   grammar_ok, translation_ok, verb_usage_ok, approved, note; judge en + bs only; no code).
   `fil batch review-import <verdicts.json>`; repair REFUSED ones, export/review again with
   a *fresh* agent (a reader who saw the first draft is no longer blind).
7. `fil site`, `pytest -q`, `node --test tests/js`, commit, publish the artifact
   (see project memory for how the artifact copy is made).

## Known gate behaviour (saves repair loops)
- English glosses are compared in base form; prefer lexicon words (e.g. "wished, willed" for شَاءَ).
- Hamzat-wasl imperatives are confirmed by the corpus table — that is expected, not a failure.
- Documented lexicon gaps live in `data/gloss_exceptions.json` (add one only with a reason).
- Composed form glosses (`fil compose build`) wrong in context: fix at the source first — a corpus
  mis-tag (form, tense, person, voice) in `data/corpus_corrections.json`, a Bosnian cell in
  `data/bs_paradigms.json`, an English rule in `fil.composition.english` (golden test); only a
  verb-specific sense or referent goes to `data/composed_gloss_corrections.json` (en, bs, why; same
  clitic words and "!"/"?" as the rule's gloss — the build refuses anything else).
  When one form's ayat need different words (سَخَّرَهَا: the camels in 22:37, the wind in 69:7), correct it
  per place instead: `data/composed_place_corrections.json` (form → surah:ayah:word → en, bs, why; same
  shape check). Type keys by copying them from a generated file: the corpus writes shadda before the vowel,
  so a hand-typed key may differ in Unicode order and is refused as stale.
- Polysemous verbs (`data/polysemous_verbs.json`: verb → senses, the first its own first sense) are composed
  place by place: `fil compose sense-sheets DIR` (each unchosen place with its ayah and English, every sense's
  gloss) → Sonnet chooses `sense` + `why` per row (re-check the non-first senses and every NONE) →
  `fil compose senses DIR` (validated, all or nothing; a missing sense is added to the verb's list first) →
  `fil compose sheets` writes the cells of each sense's own paradigm `root|form@sense` → `fil compose
  paradigms` → `fil compose build`. A form in one sense gets that gloss; in several, its row lists them ("he/it
  decreed; he/it fulfilled") and each place shows its own (`data/composed_ayah_glosses.json`). A choice whose
  form or place is gone fails the build.

## Later: the other 14 languages (several batches at once)
Build a translation memory (each unique word glossed once per language), export compact
TSV, one cheaper-model agent per language (Sonnet), import with a validating script.
