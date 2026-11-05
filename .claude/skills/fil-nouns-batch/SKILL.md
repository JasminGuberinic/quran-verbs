---
name: fil-nouns-batch
description: Add the next batch of 50 Quranic nouns to the Fiʿl study site (meaning, case table, Bosnian declension, composed glosses, 4 practice sentences, pages), token-efficiently. Use when the user says "/fil-nouns-batch", "next nouns", "dodaj još imenica", or asks to add nouns.
---

# Add a batch of nouns (Arabic + English + Bosnian)

Goal: ~600 nouns (83% of noun occurrences), 50 per batch, one batch per conversation
(docs/NOUNS-PLAN.md). Same rules as the verbs (/fil-batch): bs + en only, work from the
compact files, `fil nouns batch …` prints only failures and one-line summaries, never `cat`
large files, ask the owner (in Bosnian, briefly) before any product decision, commit and push
to study-site when done (never main, never deploy).

## Steps
1. `fil nouns batch plan next 50` → `build/nouns/batch/{batch.txt, plan.tsv, todo-meanings.tsv}`.
   It skips adverbs (بَيْن، عِند، قَبْل، بَعْد، دُون), quantifiers/pronoun-like words (كُلّ، بَعْض،
   أَيّ، غَيْر), adjectives (their own phase) and HELD_BACK nouns (إِلٰه — owner's decision) and
   prints what it skipped. A hand-picked list: `fil nouns batch plan FILE` (lemma or lemma|root
   per line; picturable ones from `data/noun_categories.json`).
2. Meanings: write `build/nouns/batch/meanings.tsv`, 10 tab-separated columns:
   `key en en_plural bs countable adverbial polysemous idafa_ar idafa_en idafa_bs` (flags y/n).
   - `en` first sense composes every gloss — use a word the CAMeL lexicon glosses
     (todo-meanings.tsv lists them; the import WARNs otherwise). `bs` first word = what the
     Bosnian declension declines (e.g. "kapija, vrata", not "vrata": pluralia tantum break agreement).
   - `countable` n for mass nouns (water, truth, punishment: no "a").
   - `adverbial` y when a bare accusative is mostly not an object: time words (يَوْمَ), حَقًّا
     "truly", رَبَّنَا "our Lord!" (vocative). Those forms keep their grammar label.
   - `polysemous` y when one sense would mislead across the Quran (عَيْن eye/spring, خَيْر
     good/better): no form of it is composed.
   - iḍāfa: a construct head that is natural with this noun as possessor, nominative,
     full harakat (`بَابُ` + الْبَيْتِ → "vrata kuće"); en/bs translate the head only.
   `fil nouns batch meanings build/nouns/batch/meanings.tsv`.
   **Collectives, singulatives, pairs** (docs/NOUNS-PLAN.md): review every lemma in
   `build/nouns/batch/collectives.tsv` (and any collective you spot yourself: herds, crops, fruit,
   peoples) into `data/noun_relations.json` — `collective` (+ `agreement` F|M|MF|MP as the Quran
   uses it, + `one`/`male`/`female` words), `singulative` (+ its `collective`), `pair` (+ `male` or
   `female`), or `ordinary`; each with a `why` citing evidence, related words as indefinite
   nominatives with full harakat (`ar`) and `lemma` lemma|root when the Quran has them. A
   collective's meaning is plural in sense ("deve", "ptice"; `countable` n). Do this before tables.
3. `fil nouns batch tables` → data/noun_tables.json (Quranic spellings first, CAMeL + gate for
   the rest; a second plural is its own row; a "plural" spelled like the singular is dropped as
   a collective). A cell CAMeL cannot make (عَصَا: it writes a vowel on the alif) may be
   documented in `data/noun_overrides.json` with a `why` — gated, never over a Quranic cell.
4. Bosnian declensions: `fil nouns batch bs-sheet` → `bs-sheet.json`; split in two and give
   each half to a **Sonnet** sub-agent (prompt: decline the first bs word, one word per cell,
   du cells as "dvije ruke/dviju ruku/dvjema rukama", genders m/ma/f/n as a possessive agrees,
   a preposition choice per Arabic preposition from the sheet's options; a collective (إِبِل, طَيْر)
   gets its sg row in the Bosnian plural — deve/deva/devama — and `"pluralForms": ["sg"]`). Import each with
   `fil nouns batch paradigms FILE` (validated: Latin Bosnian, every needed cell, allowed choices).
   Then **review the choices yourself** (one compact print): drvo → G "drveta" (not "drva");
   set a preposition to `"-"` where the verb, not the noun, decides the Bosnian case — `bi` for
   people and abstract nouns (آمَنُوا بِرَبِّهِمْ "u Gospodara", كَذَّبُوا بِآيَاتِنَا "naše znakove"),
   `ala` for رَبّ (يَتَوَكَّلُونَ عَلَى رَبِّهِمْ).
5. Sentences: `fil nouns batch wordbank`, then write `build/nouns/batch/draft-N.tsv`, 4 per noun:
   `key role arabic(target *) en bs en_glosses bs_glosses` (7 columns, `|` between glosses),
   roles `subject` (NOM), `object` (ACC), `preposition` (GEN after فِي/عَلَى/مِنْ/إِلَى/عَنْ/مَعَ or
   attached بِ/لِ/كَ), `possession` (the noun as GEN possessor after a construct noun).
   2–5 words, natural MSA, full harakat, standard spelling. The target must be a cell of the
   noun's table (or the construct form of an indefinite cell: رَبُّ الْبَيْتِ) — pick forms the table
   has (print it if unsure). A noun whose table lacks a case gets no sentence for that role
   (fill a missing cell with a documented override first when CAMeL fails: إِبِل's NOM/ACC). For a
   collective, agree as recorded: الْإِبِلُ تَأْكُلُ (feminine); translate in the plural ("ptice"). `fil nouns batch check FILE` until clean, then `draft FILE`.
6. Blind review: `fil nouns batch review-export` → `blind.json`; ONE fresh general-purpose agent,
   strong model (opus), judges grammar (every case ending!), en + bs translation, noun usage and
   content policy, writes verdicts `{id, grammar_ok, translation_ok, noun_usage_ok, approved, note}`;
   `fil nouns batch review-import FILE`. Repair refused ones in a new draft file, export again,
   and review with a *fresh* agent.
7. `fil nouns batch status` (what each noun still lacks, `relation` included), `fil pages` (log to a file; report only
   errors), `pytest -q`, `node --test tests/js`, commit, push.

## Content policy (as for verbs)
No Quranic wording (check famous phrases: بِلِسَانٍ عَرَبِيٍّ، رَكِبَا فِي السَّفِينَةِ، وَبِالنَّجْمِ هُمْ
يَهْتَدُونَ), nothing said in God's name or about God, no "؟", gentle everyday content. Nouns
whose ordinary sense is God (رَبّ) get sentences in a human sense (رَبُّ الْبَيْتِ "the owner of
the house"); nouns that can only speak of God or gods (إِلٰه) are held back for the owner.

## Known gate behaviour (saves repair loops)
- English glosses are compared with CAMeL's in base form and American spelling (color, traveled);
  irregular past forms the base-form table lacks fail (flew, swam) — use the present or another
  verb. Lexicon-only senses: "purchased" (اشْتَرَى), "emancipated" (أَعْتَقَ), "the remedy" (الدَّوَاءُ).
- A lexicon gap gets a documented entry in `data/gloss_exceptions.json` (أَغْلَقَ "close", عَذْب
  "fresh" were added in the pilot) — never a wrong English gloss to please the gate: the
  reviewer refuses "locked" for أَغْلَقَ.
- Voice gate: `fil pages` FAILS when a noun sentence, table cell, case example or headword has no
  checked voice (the two readers in fil.speech disagree). Fix the reader with a golden test in
  tests/test_speech.py (the model's phonetiser has known slips: wā/kā read short, tanwīn before
  shadda, "net" for صَنَعْتُ) — `data/noun_unvoiced.json` (text → why) is the last resort.
- Fixed in batch 2 (no longer needed): Uthmani ٱلصَّلَوٰة/ٱلْحَيَوٰة/ٱلَّيْل now key like imlāʾī
  spellings in the table lookup, and the voice reads ىٰ, undotted ىّ and بِٱلَّيْلِ correctly.
- عَذَاب is torment/punishment, not everyday pain (refused once).
- An object noun without a possessor can be unnatural (غَسَلَ الْأَطْفَالُ الْأَيْدِيَ): Arabic says
  أَيْدِيَهُمْ, which the table cannot hold — choose another sentence.

- Batch 2 (2026-11-05): the planner lets through adjectives the corpus files as nouns
  (مُبِين، خالِد، قَلِيل، كَثِير، أَكْثَر، آخَر، عَزِيز، غَفُور، بَصِير، أَعْلَم) and أَحَد/جَمِيع — add
  them to `NOT_TAUGHT_AS_NOUNS` (fil/nouns/selection.py, NFC-matched) and re-plan until clean;
  God-only nouns (رَحْمٰن) go to `HELD_BACK`.
- Plural-only lemmas (آباء، أَصْحاب) get no table from CAMeL: document the P row in
  `noun_overrides.json`. Override keys are number|state|case, so a second-plural row (P2) cannot
  be targeted — leave its gaps. A relation's `lemma` must spell the related word's letters
  (the corpus's امْرَأَت|مرأ fails for امْرَأَةٌ): omit it then. Copy relation keys from
  batch.txt — a key typed with shadda/vowel in the other order is silently "missing" in status.
- Draft spelling: `*بِالْ…` (star before the attached preposition, never `بِ*`); a definite
  ابْن is written الْاِبْن in the table — use construct ابْنُ … instead.
- Lexicon gaps for Quranic senses are root-keyed in gloss_exceptions.json (angel, guardian,
  favor, righteous, warner, witness, evil added). Glosses that fail: sought → "requested",
  boy (الْوَلَد) → "child", big → "large", buys → "purchases", policeman → "police officer",
  topic (مَوْضُوع) → "subject", drew → "sketched"; قَبْلَ/بَعْدَ are not prepositions for the role.

## Pilot lessons (2026-11-05, 50 nouns)
- 198 sentences drafted, 6 refused by the blind reviewer (3%), all repaired and approved.
- Form glosses: the composer skips what it cannot know — readings that differ, عَن, vocatives,
  emphatic la-, a bare accusative after إِنَّ/كَانَ, second plurals (عُيُون "springs" ≠ أَعْيُن "eyes").
