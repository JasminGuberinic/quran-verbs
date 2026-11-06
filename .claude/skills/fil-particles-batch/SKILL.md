---
name: fil-particles-batch
description: Add the next batch of Quranic particles ("Čestice / Particles": what each does, its effect on the next word, its uses with corpus-tagged ayat) to the Fiʿl study site, mechanically and token-efficiently. Use when the user says "/fil-particles-batch", "next particles", "dodaj još čestica", or asks to add particles.
---

# Add a batch of particles (bs + en)

Goal: the Quran's small words — what each does, what it changes in the next word, its uses (docs/PARTICLES-PLAN.md).
One batch (~10–25 particles) per conversation. Rules as everywhere: bs + en only, never ask the owner linguistic
questions (decide, write the decision in the particle's `notes`), commit and push to study-site (never main, never
deploy). Engine: src/fil/particles/ (pure: model, gate), corpus reader fil.corpus.particles, stage
src/fil/stages/particles.py (CLI, the corpus concordance), cards fil.stages.particle_site, pages
fil.stages.particle_pages + fil.pages.particle_render.

## Content rules (sacred)
- Our own words, grounded in classical grammar: Ibn Hišām, *Muġnī al-labīb* (meanings of each particle);
  Sībawayh, *al-Kitāb* where named. Attribute single views ("Prema Ibn Hišāmu…", "According to the Basran
  grammarians…"); never put a view in a named scholar's mouth you cannot vouch for — hold it back, note it.
- Never "always/never/only" without checking `fil particles find` output (e.g. iḏā is not only future,
  surprise iḏā is not only after فَ; لَمْ also negates timelessly — 112:3).
- Name contested readings (qirāʾāt: 80:4 فَتَنفَعَهُ is Ḥafṣ's subjunctive) and grammarians' disagreements
  (لَا of the kind: Basrans "fixed on fatḥa in the place of the accusative").
- Bosnian per Korkut (Allah, ajet, Kur'an, Musa, Ibrahim; ijekavica); English Sahih International style. bs and
  en must say the same thing — the reviewer flags every drift (lišće/straw, pogledao/considered).
- Content policy: respectful of Allah and the prophets.

## Working in an agent worktree
- Symlink `data/qac`, `data/quranhive`, `data/translations` to the main repo's; copy `build/nouns/*.tsv`; link
  `build/{speech,recitation,compressed}-cache`. Run `PYTHONPATH=src ~/Development/quran-verbs/.venv/bin/python -m
  fil.cli …` and `… -m pytest -q`. Scratch scripts in `build/scratch/` (gitignored); write them with the Write tool
  (the isolation guard refuses complex heredocs).

## Steps
1. `fil particles frequency` → every (lemma, tag) by count. Pick the next particles; a particle is one corpus
   lemma (`LEM:`), its uses are tags (with family: `NEG|FAM:إِنّ`).
2. For each use: `fil particles find LEMMA TAG [N]` → the shortest ayat holding it, `s:a:w`, and the marker of the
   next word. Pick 1–3 well-known ayat whose marked word shows the effect you claim; pin the word (`s:a:w`) when an
   ayah holds the use twice (the gate says so). Cite only ayat the corpus tags as the use you claim.
3. Write the content as Python in build/scratch (helpers `T(bs,en)`, `A(ref,bs,en)`, `U(key,kind,tags,title,
   explanation,ayat,effect)`, `P(slug,arabic,lemma,meaning,grammar,uses,…)`), then a merge script: start from HEAD's
   data/particles.json, add the particles, fill every `count` as the sum over the uses' tags
   (`CorpusParticleConcordance.from_corpus().occurrences(lemma, tag)`), sort by count, and dump with one-space
   indent and ≤ 120-character values on one line. Kinds are fil.particles.model.KINDS (a new kind needs its
   bs/en label in site/ui.js `PARTICLE_PAGE.kinds`). Slugs: house transliteration, ʿayn/hamza dropped, the more
   frequent keeps the plain slug (أَنْ `an`, عَنْ `an-2`). Prepositions name their fil.nouns.bosnian key.
   Proclitics are written with a tatweel (بِـ) and voiced without it automatically.
4. `fil particles check` → only problems + a summary line (wrong count, unknown tag, an ayah that does not hold
   the use, a word to pin, a next word that does not show the effect). Fix until 0. tests/test_particles.py pins
   the number of stored particles: update it with the batch.
5. `fil particles review-export SLUG …` → build/particles/blind.json (only the new particles). Give it to a FRESH
   Sonnet general-purpose agent as a blind reviewer (grammar, attributions, overstatement, the cited ayah and
   marked word, bs/en drift, Korkut style, content policy; OK or FLAG + rewording per claim id). Apply every flag
   (reword, attribute, or hold back and note), re-run `check`.
6. `fil pages` (log to a file; headwords are voiced by the checked synthetic voice — a disagreement stops the
   build), `pytest -q`, commit, push.

## Pilot (2026-11-06): 22 particles
وَ · مِنْ · لِـ · فَـ · بِـ · مَا · لَا · فِي · إِنَّ · عَلَى · إِلَى · إِنْ · إِلَّا · أَنْ · عَنْ · إِذَا · قَدْ · أَنَّ · لَمْ · ثُمَّ · كَـ · لَنْ.
Lessons:
- First drafts guessed word numbers wrong and cited ayat the corpus tags differently (31:13 لَا تُشْرِكْ is NEG, not
  PRO; 37:35 لَآ إِلَٰهَ is plain NEG): always take refs from `find`.
- What the reviewer flagged: Sībawayh's term is al-ilzāq; "after قَالَ always إِنَّ" (only for a quotation);
  لَا of the kind "accusative" (Basrans: fixed on fatḥa); fāʾ of consequence also after a hope (لَعَلَّ) and 80:4 is a
  qirāʾa question; إِلَى = maʿa is Ibn Hišām's, the Basrans read taḍmīn; "never" in English glosses of لَنْ while
  the page says لَنْ is not "never"; bs/en drift in quoted renderings. Write those safeguards in the first draft.
- Next by frequency: أَ (INTG 507), يَا (VOC 361), إِذْ (T 309), أَوْ (280), لَوْ (189+12), لَـ EMPH (1001), بَلْ (127),
  مَنْ (REL/COND/INTG), حَتَّى (142), لَعَلَّ (129), هَلْ (93), لَٰكِنَّ/لَٰكِنْ (130), سَ/سَوْفَ (161), لَمَّا, أَمْ (137).
