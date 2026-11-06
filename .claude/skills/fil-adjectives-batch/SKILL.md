---
name: fil-adjectives-batch
description: Add the next batch of 50 Quranic adjectives to the Fiʿl study site (meaning, two-gender agreement table, agreement examples, 4 practice sentences, pages), token-efficiently. Use when the user says "/fil-adjectives-batch", "next adjectives", "dodaj još pridjeva", or asks to add adjectives.
---

# Add a batch of adjectives (Arabic + English + Bosnian)

Goal: the Quran's adjectives (428 QAC ADJ lemmas + adjective-like participles/intensives), 50 per batch,
one batch per conversation (docs/NOUNS-PLAN.md, "Adjectives"). Same rules as the nouns (/fil-nouns-batch):
bs + en only, compact files, `fil adjectives batch …` prints only failures and one-line summaries, never
`cat` large files, decide wording and translation yourself (Korkut, Sahih International) and report it, hold back only content-policy cases (God-only senses) for the owner, commit and push to
study-site when done (never main, never deploy). Engine: src/fil/adjectives/ (pure), stage
src/fil/stages/adjectives.py, pages fil.stages.adjective_site/adjective_pages + fil.pages.adjective_render.

## Steps
1. `fil adjectives batch plan next 50` (or `plan FILE`, one lemma or lemma|root per line) →
   build/adjectives/batch/{batch.txt, plan.tsv, todo-meanings.tsv}. The planner merges a separately
   lemmatised feminine (كَثِيرَة) into its masculine's count, skips elatives (أَكْبَر → shown on كَبِير's
   card), ordinals/numbers, idioms, ḥāl-only participles and lemmas taught as nouns
   (`NOT_TAUGHT_AS_ADJECTIVES`, fil/adjectives/selection.py) and HELD_BACK (God-only senses).
   Past ~rank 350 most candidates are not teachable: read every planned lemma, add a reason for each
   one you refuse to `NOT_TAUGHT_AS_ADJECTIVES` (elative, circumstance, substantive, takes an object,
   Quranic phrase, a plural/feminine lemma, a near-synonym on another card, `FA_UL`) and re-plan until
   all 50 are teachable (batch 2 took 9 rounds; `plan next 140` previews the tail at once). Decide
   wording yourself (Korkut for bs, Sahih International for en); only a God-only sense is held back.
   فَعُول adjectives (شَكُور, كَفُور, رَءُوف, فَخُور) have one form for both genders (امْرَأَةٌ شَكُورٌ) and
   are refused (`FA_UL`), as are women-only invariables (عَاقِر, عَقِيم). Read
   plan.tsv's feminine-lemma and feminine-forms columns: a feminine lemma that is a noun in use
   (بَيِّنَة, حَسَنَة "good deed", سَيِّئَة "misdeed", طائِفَة, مَيْتَة "carrion", حَيَّة "snake", كَبَائِر) gets
   feminine_lemma n.
2. Meanings: write a `~`-separated file and convert to TSV (13 columns, NO header):
   `key en bs bs_short bs_long feminine feminine_lemma(y/n) pattern category nouns masculine_plural elative_en elative_bs`
   - `en` first sense composes the examples ("a large house") — check it reads with the chosen nouns
     (refused: "few food", "safe men", "pleasant men", "a bad work", "faithful" = believer → "trustworthy").
   - `bs_short`/`bs_long`: the short and long masculine nominative (velik/veliki, mudar/mudri, zalutao/
     zalutali); bs_long is one lowercase word in -i (arapski, drugi, obližnji). Bosnian declines by rule
     from it (fil.adjectives.bosnian), agreeing with the *Bosnian* noun's gender (شَجَرَة → "veliko drvo").
     "blizak" is emotional closeness (use obližnji for places); "poznat" reads "famous" (određen for fixed).
   - `feminine`: the feminine singular as the dictionary writes it (كَبِيرَة, أُخْرَى, عَمْيَاء, بَيْضَاء).
   - `pattern` (فَعِيل, فاعِل, مُفْعِل, أَفْعَل…): أَفْعَل and فَعْلَان singulars are declined without nunation.
   - `category`: size_quantity people_qualities condition moral intensity time_distance knowledge_clarity colours other.
   - `nouns`: m,f,things,people — studied noun lemmas (`-` for none). The card's examples are built from
     their table cells: masculine → indefinite/definite/predicate, feminine → feminine (+ the elative's
     second noun), things → plural of things (feminine singular), people → plural of people (needs a
     masculine plural). Give people only where "X-men" is natural (حكماء, أقوياء, صابرون), things only
     where the adjective describes things. A noun without a P row (شَجَرَة, رَجُل, طائِر) cannot be a plural noun.
   - `masculine_plural`: `-` (none), `sound` (-ūna), or a broken stem (كِبَار, عُظَمَاء — a stem in -āʾ is a
     diptote). Where the Quran's own plural is broken, give that same stem (عُلَمَاء, أَغْنِيَاء, كِرَام) so the
     rule fills the cells the Quran lacks (its Uthmani spelling carries a case ending).
   - elative en/bs only where "The house is bigger than the tree" is natural (كَبِير, صَغِير, قَرِيب).
   `fil adjectives batch meanings FILE.tsv` (WARNs on lexicon glosses; noun keys must be studied).
3. `fil adjectives batch tables` → data/adjective_tables.json: Quranic spellings first, CAMeL asked one
   gender at a time (strict), then the rule (fil.adjectives.declension) for what is regular; prints
   `RULE≠CAMeL` lines if the rule ever disagrees with CAMeL (0 in the pilot over 988 cells) and the
   adjectives whose rows are not SDP on both sides. Hamza- and alif-maqṣūra-final stems (بَرِيء, سَيِّئ, أَعْمَى,
   أُخْرَى) are refused by the rule: document their cells in data/adjective_overrides.json
   (`{key: {"M"|"F": {"S|indefinite|NOM": {text, why}}}}`, one script with a `row()` helper). The corpus
   reader (fil.corpus.nouns) reads an alif-maqṣūra or -āʾ noun without a possessor, and a genitive in
   fatḥa, as indefinite (أُخْرَىٰ, أَعْمَىٰ, أَوْلِيَآءَ, أُخَرَ are attested); a fuʿal diptote's nominative /
   accusative (أُخَرُ) still reads as construct and needs a documented cell. A broken plural stem the
   rule declines is a triptote unless it ends in -āʾ: never give a mafāʿīl stem (مَجَانِين) — use "-".
   An elative ending in alif maqṣūra (أَعْلَى) is not shown: give no elative for it.
4. `fil adjectives batch examples` prints each card's agreement examples (Bosnian) and which kinds are
   missing — fix nouns in meanings before review. A noun whose cell is missing drops its example
   (عَصَا, دُعَاء indefinite; شَيْء definite; ثَمَرَة, مِصْبَاح indefinite plural): pick another. A Bosnian
   collective plural (djeca, braća, odjeća) needs `"singularForms": ["pl"]` in noun_bs_paradigms.json
   so it agrees in the feminine singular ("radosna djeca").
5. Sentences: `fil adjectives batch wordbank`, then write `~` lines `key~role~ar(*target)~en~bs~en|glosses~bs|glosses`,
   4 per adjective: masculine, feminine (attribute right after its noun), predicate (after a nominative
   subject; accusative after كَانَ/صَارَ), plural (people → plural, things → feminine singular). The
   described noun must be a cell of a studied noun (construct allowed for a predicate's subject:
   اسْمُ الشَّاعِرِ خَالِدٌ). Convert with a script asserting word count = gloss counts, `check` until clean, `draft`.
   Divine-Name adjectives get human senses (a wise man, a merciful mother); "X is other" has no predicate
   (آخَر keeps 3 sentences). Bosnian: an indefinite masculine singular nominative attribute takes the
   short form ("star grad", "Vidio sam dug put"); the definite the long one ("stari grad").
   Drafting can go to two general-purpose agents (25 adjectives each, own output file, `check` only);
   fill in every placeholder of the brief before sending it.
6. `fil adjectives batch review-export` → blind.json holds sentences (`s:` ids) and agreement examples
   (`e:` ids); split it in two and give each to a FRESH opus general-purpose agent (sentences: grammar_ok,
   translation_ok, usage_ok, approved, note; examples: approved, note), ids copied programmatically.
   `review-import` each file. Repair refused sentences in a new draft file; for refused examples change
   meanings (en, bs, nouns), delete the refused entries from data/adjective_example_reviews.json, re-export,
   review with a fresh agent. Only approved examples ship.
7. `fil adjectives batch status`, `fil pages` (log to a file; voice gate covers adjective cells, examples,
   sentences), `pytest -q`, `node --test tests/js`, commit, push.

## Known gate behaviour (pilot, 2026-11-06)
- Gloss exceptions added (root-keyed): knowledgeable ع.ل.م, merciful ر.ح.م, foul/rotten خ.ب.ث, lost/stray
  ض.ل.ل, praiseworthy ح.م.د and حمدة (CAMeL reads حَمِيدَة as a name). Lexicon words that pass: large (not big),
  great (عظيم), gentle (حليم), quick (سريع), compassionate, malicious, faithful, little/few, with us (عِنْدَنَا).
- Failed → accepted: fell (نَزَلَ) → rephrase, did (قَامَ بِـ) → فَعَلَ, flew → يَطِيرُ flies, spent (قَضَى) → عِشْنَا lived,
  seller → vendor, help (مُسَاعَدَة) → assistance, tasks → actions, meet (اجْتَمَعَ) → met, bag → suitcase.
- Reviewer refusals: خَبِيث is not "rotten" fruit (فاسِد) — use it of people/words/water; أَيَّامٍ مَعْلُومَةٍ and
  الْيَوْمُ الْآخَرُ echo the Quran; living whales pulled out by one fisherman is not believable.
- Batch 3 (2026-11-06): the list is exhausted. After batch 2 only 40 candidates were left, all Quranic
  hapaxes (rank 2400+); 35 were refused and 5 shipped (غَرْبِيّ, قَصِيّ, لَيِّن, مُرْتاب, وَهّاج). A further
  batch needs a policy change (HELD_BACK, a recorded refusal reconsidered, or new candidates beyond QAC ADJ
  and NOT_TAUGHT_AS_NOUNS' "adjective…" entries) — `plan next 50` then plans 0.
- The planner pairs a feminine lemma by letters alone: لِينَة (a palm tree, 59:5) was offered as the feminine
  of لَيِّن. Read the feminine-lemma column; a different word gets feminine_lemma n.
- Table cells write a doubled letter with its vowel (جَبَّارٌ, شَكًّا): fil.nouns.spelling.with_voweled_shadda
  mends CAMeL's جَبّارٌ / شَكّاً at the adapter and the rule's الصّابِرُ (from a lemma written صابِر); the gate
  refuses a bare shadda. data/adjective_example_reviews.json is keyed by the example's Arabic text, so any
  engine change that respells cells must re-key it (else approved examples silently drop): compare
  `review-export`'s example count before and after.
- Gloss gate, batch 3: لَيِّن needs the root exception ل.#.ن (soft, mild; the lexicon has only "flexible");
  وَهَّاج passes as "glowing" (not "blazing"); اللَّيْلَةَ "tonight" and سَأَلَ "questioned" fail (use "asked");
  CAMeL does not read فُرُش as the plural of فِرَاش — keep it to the agreement examples.
- Example nouns whose own en/bs senses differ get refused: بَاب (en "door", bs "kapija"), قَرْيَة (en "village",
  bs "naselje"). سُوق is mostly feminine (التأنيث فيها أغلب) — never a model of masculine agreement (شَرْقِيّ's
  card still uses it: a follow-up). Pick an unambiguously masculine noun (جانِب, بَلَد, نَجْم).
- Examples are shown in standard spelling (fil.nouns.spelling.imlai folds the Quran's ٱ, dagger alif,
  ءَا, undotted ى, madda only where spelling_key says it is the same word).
