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

- Batch 3 (2026-11-05): more adjectives/quantity words to skip (سَمِيع، قَدِير، مُسْتَقِيم، مَيِّت،
  أَحْسَن، أَشَدّ، واحِدَة، طَيِّبَة); آلاء (only "your Lord's favours") is HELD_BACK.
- Before writing glosses, print CAMeL's glosses for doubtful words in ONE call
  (`service.camel_analyzer()` from fil.stages.noun_batch, `{x['root'], x['gloss']}`): it shows
  the root key a gloss exception needs (سُلْطَان is س.ل.ط.ن, four letters) and the accepted word
  (خَضَعَ "was subject", not "submitted"). Glosses that failed: the shepherd (الرَّاعِي) → farmer,
  the old man (الشَّيْخ) → grandfather, spacious, talked (تَحَدَّثَ → تَكَلَّمَ spoke), spent (قَضَى),
  passed (مَضَى → مَرَّ), erred, exposed (كَشَفَ "discovered"), cared (اهْتَمَّ، اعْتَنَى), graze.
- A sound-feminine-plural ACC override (الْأُمَّهَاتِ) fails the gate when the corpus files the
  plural as broken — leave that gap. data/gloss_exceptions.json is indented 2, the noun_*.json 1.
- A Bosnian plurale tantum (grudi for صَدْر) uses the collective mechanism: sg row in the plural,
  `"pluralForms": ["sg"]`. Re-check the Sonnet halves' first word against the sentences you
  plan (hvala→pohvala, skupina→tim, naknada→nagrada) and fix with a small paradigms file.
- Tell the blind reviewer to copy ids from blind.json programmatically: a retyped id (marks
  reordered in قُوَّة) imports as "unknown"; remap by the `#n` suffix. حَمْد with no agent sounds
  reserved for God (give it one: حَمْدَ النَّاسِ); a prize is جَائِزَة, not جَزَاء; صِرَاط only figurative.

- Batch 4 (2026-11-05): skipped سَواء، غافِل، أَجْمَع، أَكْبَر، حَيّ، غَنِيّ، سَبْع، أَعْمَى، مُسَمًّى،
  ساجِد، صابِر; HELD_BACK جَحِيم، جِنّ (no everyday human sense). Read batch.txt for adjectives/
  participles-as-ḥāl BEFORE writing meanings — each skip re-plans and pulls in a new noun.
- Tables hold only the numbers the Quran uses: مُنافِق، مُكَذِّب، ظُلُمَة are plural-only — draft them
  in the plural; a Bosnian word with no natural plural (tama) fills the pl row with its singular forms.
- Draft key = batch lemma (امْرَأَت, not امْرَأَة). A construct of a hamza-final indefinite cell
  (دُعَاءَ أُمِّهِ) is "not a cell" — use the definite. Uthmani-only iNOM (نَبَؤٌا۟) likewise.
- Print the gloss table of the failing words once (CAMeL `gloss` per word) and fix all in one pass.
  Failed → accepted: smell→odor, accuracy→correctness, founded→established, comforts→relaxes,
  amuses/delights→gladdens, watched (رَاقَبَ)→observed, seller→vendor, عَمَل deed→action,
  common→widespread, frightening→frightful, await→wait for, ترك abandoned (use رَفَضَ rejected), brown.
- The Sonnet halves put bi "" everywhere: set bi "-" for people and abstract nouns (and min "od"
  for abstracts) with one scripted fix file over both halves.
- Refused as nouns by the reviewer: جُنَاح (only the idiom لَا جُنَاحَ; offense is جُنْحَة) → HELD_BACK;
  حَمِيم (MSA adjective صَدِيقٌ حَمِيمٌ) → skipped; bare الطَّائِفَة reads "sect" — say طَائِفَةٌ مِنَ السُّيَّاحِ.
  To drop a noun mid-batch: delete its key from noun_meanings/noun_bs_paradigms/noun_sentences,
  skip/hold it, save batch.txt, `plan next K`, then concatenate the old batch (minus it) + the new K.

- Batch 5 (2026-11-05): skipped أَقْرَب، مُصَدِّق، مُعْرِض، عالِم، قائِم، مُهْتَدي، آمِن، أَظْلَم، حُسْنَى،
  أَلْف، خاشِع، شاكِر، ضالّ، قادِر، مُهِين, and ابْتِغاء (always a bare accusative "seeking", مفعول لأجله — and a
  construct of its hamza-final cell is not a cell); HELD_BACK سَعِير، تَنزِيل، مَرْجِع (Quranic sense only
  about Hell/revelation/return to God; MSA sense differs). Edit both lists with a script that copies
  spellings from batch.txt via NFC (typed shadda order misses), and re-plan until clean BEFORE meanings.
- meanings.tsv has NO header line (a header is parsed as a noun: "key: no root").
- Gloss exceptions (root-keyed) added: harm ض.ر.ر، scheming م.ك.ر، shade ظ.ل.ل، indecency ف.ح.ش،
  spendthrift س.ر.ف، wrongdoing ن.ك.ر، custom س.ن.ن، message ب.ل.غ، adornment ز.#.ن، dust ت.ر.ب. The
  meanings import still WARNs for them (it reads the lexicon only) — the sentence gate honours them.
- Failed → accepted: fear (تَخَافُ)→flee (تَهْرُبُ), tied→ties (present), next→following, brown (بُنِّيّ)
  fails → red, professor (أُسْتَاذ), safeguards (يَحْرُسُ), went against (خَالَفَ), pursuit (اتِّبَاع),
  harvested (قَطَفَ), made happy (أَسْعَدَ), sadness (حُزْن), tie (رِبَاط), connection (صِلَة), precise
  (دَقِيق), faithful (أَمِين), found out (عَلِمَ بِـ), costly (غَالٍ), cold/coldness (بَارِد، بُرُودَة),
  the dominion (الْمُلْك), were afraid (خَافَ), loses (يُضَيِّعُ), form (شَكْل), polite (لَطِيف), the young
  (الصَّغِيرَة), characteristic (صِفَة), elevated (مُرْتَفِع). Refused: relief (رَاحَة، الْفَرَج), step (دَرَجَة).
- Sonnet halves: check -ka nouns' D/L (poruka → "poruci", not "poruki") in the one compact print.
- Reviewer refusals: دُبُر reads as anus/buttocks in MSA → HELD_BACK (dropped mid-batch; والِد came in);
  bare الْمَوْلَى reads as God → make the human explicit (مَوْلَى الْبَيْتِ); الْحَرَج alone is
  "embarrassment"; الْقِسْط next to a sale is "installment"; a bs gloss must agree with the bs
  sentence's noun (temperatura → "je visoka"). The gate now makes construct cells of alif-maqṣūra
  indefinites (مَوْلًى → مَوْلَى) — document the indefinite cells with an override first.

- Batch 6 (2026-11-05, 195 sentences, 15+1 refused in 2 rounds): skipped numbers/quantities (اثْنَيْن، ثَلاثَة، إِحْدَى، ضِعْف، عِدَّة), بَغْتَة (adverb),
  حَسْب, and adjectives/participles-as-ḥāl (حافِظ، غالِب، مُفْلِح، أَدْنَى، أَصَمّ، بَرِيء، تَوّاب، حَفِيظ، حَنِيف،
  مُعْجِز، أَوْلَى، رَءُوف، عَلِيّ، قَوِيّ، مَجْنُون، مَعْلُوم، مُخْلِص، أَحَقّ، رَواسِي، سَرِيع). HELD_BACK: رِضْوان، خالِق،
  عابِد، قَدَر (God only), نُطْفَة (sperm), شِيعَة (MSA "Shia"), جِنَّة (jinn/madness), رِسالَة، سُورَة (revelation
  only), شَفِيع، صُور (the unseen), طُور (the Mount; MSA "stage"), بَغْي (lexicon reads "whore"). Substantive
  participles stay (ظالِم، مِسْكِين precedent: فَقِير، جاهِل، ناصِر، عامِل). `skiphold.py`-style script: one
  call per round edits both lists from batch.txt spellings; expect ~6 re-plan rounds.
- Read todo-meanings.tsv's FIRST lexicon gloss for every word: it exposes vulgar readings (بَغْي) and
  merged lemmas. The corpus lemma هَواء|هوي is mostly هَوَى "whim" (its attested cells are ٱلْهَوَىٰ) —
  print the attested cells of a doubtful lemma before meanings; held back mid-batch.
- Dropping mid-batch also needs its key removed from data/noun_tables.json (tables keep orphans:
  جُناح، حَمِيم are still there from batch 4/5).
- `plural_kind` now treats a plural-only lemma spelled with its own sound ending (سِنِين) as sound
  masculine, so its overrides (السِّنُونَ) pass the gate. Gloss exceptions added: crops ز.ر.ع/ح.ر.ث,
  evening ع.ش.#, calf ع.ج.ل, sin خ.ط.#. هُزُو has only the Uthmani هُزُوًا (MSA هُزْء): no sentences.
- Failed → accepted: fell (نَزَلَ "descended" → سَقَطَ), جَمَعَ collected → gathered, نَادَى → saw,
  انْتَهَى → تَوَقَّفَ stopped, مُنْتَشِر widespread → prevalent, بِسُرْعَةٍ → سَرِيعًا quickly, سَرِيع quick,
  الْوَفِيّ → الْأَمِين faithful, لَيِّن flexible, صَعْب difficult, مَحْفُوظ preserved, حَفِظَ → كَتَمَ concealed,
  أَخْبَرَ notified, الصِّدْق sincerity, طَبَق dish, عُرُوق (roots) → جِسْم body, عَاصِفَة (tempest) → رِيح wind,
  تَنْفَعُ fails, إِلَى = "to" (not "until"). The gl helper (print `root:gloss` per analysis) misleads on
  definite words (shows "the") — query the bare word.
- Voice: a wāw/yāʾ carrying tanwīn is a consonant (هُزُوًا huzuwan) — fixed in fil.speech.
- Reviewer refusals: أَرْحام as "kinships" (use "relatives", bs rodbina; never as the agent who
  visits — only visited/kept in touch with: صِلَةُ الْأَرْحَامِ), رِجْس is moral/ritual impurity
  (nečistoća), not dirt; ضَرّ is a person's harm/hardship (nevolja) — damage to things is ضَرَر;
  اسْمُ النَّاصِرِ reads as the name al-Nāṣir; bare الْخَيْرَات reads "good things" — give it a
  deeds context; الْخِزْيُ صَعْبٌ is unidiomatic (مُؤْلِمٌ). Changing a bs word after approval:
  delete that noun's approved sentence from noun_sentences.json (`draft` SKIPs an existing role).

- Batch 7 (2026-11-06, 216 sentences, 14+2 refused in 3 rounds): 5 re-plan rounds. HELD_BACK: تَذْكِرَة (MSA ticket),
  رِجْز، عِبادَت، فَصْل (day of decision), قَرار (MSA decision), غُرُور (MSA vanity), غِلّ (corpus merges غُلّ
  shackles: its plural أَغْلال), مَآب، مَبْعُوث، مُبَشِّر (MSA missionary), شِمال (MSA north), صُحُف (MSA
  newspapers), طاغُوت، فَرْج, and mid-batch مَغْرِب (bare الْمَغْرِب reads Morocco — refused 4/4). Check the
  MSA reading of every bare definite BEFORE meanings: الْقَرِين reads the jinn companion (add الصَّالِح),
  الْمُسْتَقَرّ reads "the stable" (use a construct: مُسْتَقَرُّ الْعَائِلَةِ), اللَّيْلَةَ = "tonight".
- Plural-only/dual-only lemmas (أَساطِير، خَزائِن، مَنافِع، والِدَي) and possessive-only singulars (عُنُق، عَقِب)
  get NO table row: write the whole row in noun_overrides.json in one script (a `tri(row, defs, indefs, why)`
  helper); a missing row is created by its overrides. Diptote patterns (فَعْلاء، فَعائِل، مَفاعِل، فُعَلاء)
  need their indefinite cells documented. CAMeL vowels لَعِب as لَعْب: the definite fails the gloss gate
  until a root exception exists (ل.ع.ب "play").
- A meanings line typed by hand imports fine, but copy keys from batch.txt anyway. Glosses that failed →
  accepted: led→guided, reviewed→examined, happened (وَقَعَ), endured (تَحَمَّلَ), sad/tragic (مُحْزِن: use
  مُؤْلِم painful), forbidden→prohibited, profitable→lucrative, small (قَلِيل)→little, bag→briefcase, scarf,
  statement (بَيَان), academic, hung (عَلَّقَ), effective/impressive (مُؤَثِّر: avoid), goldsmith→jeweler,
  good (صالِح)→upright/righteous, manners→morals, تَجْمَعُ "brings together"; مِنْ "against/out of" fails (use "of"/"from").
- Voice: the God-name rule read اللَّهْو as allāhw — fixed in fil.speech (the hāʾ must end the word). Run
  `pytest tests/test_noun_site_gates.py -k read_alike` before `fil pages`: it names silent sentences in 90 s.

- Batch 8 (2026-11-06): 8 re-plan rounds. A dual lemma (أَبَوان، أُنثَيَيْن, like والِدَي) gets no card — skip
  it as "dual (on its singular's card)". Skipped participles/elatives/numbers (مُبارَك، مُتَّكِئ، مُدْبِر، مُشْفِق،
  مُقَرَّب، سابِق، عاكِف، غابِر، قاعِد، كارِه، مُرِيب، مُنِيب، مُتَكَبِّر، مَفْعُول، كَبِيرَة، بالِغ، جاعِل، أَوّاب، أَسْفَل،
  أَبْقَى، أَهْدَى، أَبْكَم، أَرْبَع، اثْنَتَيْن، سِتَّة، عَشْر، نِصْف، ثُلُث), بُعْد (always the curse بُعْدًا) and صَفّ (always
  صَفًّا "in rows"). HELD_BACK: مُحْصَنَة، نُزُل (MSA hotel)، جانّ، زُبُر، سَوْءَة، حِجاب (MSA headscarf)، قَدْر، فُرْقان، هاد،
  مِهاد (Hell's bed)، هَدْي (sacrifice; MSA guidance)، أَخْذ (God's seizing)، أَنداد، أُمِّيّ. Print attested forms
  (`att.py`: Counter of o.word_text per NFC lemma over noun_stage.load_occurrences()) for every doubtful
  lemma in ONE call before deciding: it exposed بُعْد، صَفّ، هاد، أَخْذ.
- A word CAMeL cannot analyze at all (يَمّ) needs `spelling:<form>` gloss exceptions per used form —
  a root key never matches. Indefinite رِبًا (alif with fatḥatān) fails the cell gate: leave it.
- spelling_key now drops the silent alif after a silent-wāw seat (ٱلرِّبَوٰا۟ = الرِّبَا); the voice reader
  now keeps an alif after kasra silent (مِائَة، الِاتِّجَاه). A manqūṣ definite GEN attested as ٱلْوَادِ is no
  cell for الْوَادِي, and its construct وَادِي is not made — واد has no possession sentence.
- Voice: fil.speech now drops a letter marked ۟ (U+06DF, never pronounced) and reads a bare وٰ as ā
  (ٱلرِّبَوٰا۟ ar-ribā, ٱلْبَلَٰٓؤُا۟, ٱلصَّلَوٰة aṣ-ṣalāh) — Uthmani table cells and case examples were silent.
- Failed → accepted: ripened→matured, ready (جَاهِز)→prepared, bothered (أَزْعَجَ), decreased (خَفَّفَ), came
  true→was realized, told (حَكَى)→related, تَفْسِير→explanation (else "exegesis"), fed→feeds, enjoyable→
  pleasing, أَنْهَى fails, حَلَّ fails, تَحْقِيق→achievement, تَحَمَّلَ fails→faced, يَصْدَأُ and يُضَيِّعُ have no
  analysis, صَادِق→truthful, مَرَّتَيْنِ→two times, الْفُصُول→sections, نُقْطَة→point.
- Reviewer refusals: bare الْإِخْرَاج next to مُدِير reads "directing" (give it an object: إِخْرَاجُ الطَّالِبِ);
  bare الْجَهْر is not "loudness" (الْجَهْرُ بِالْكَلَامِ); الْحَمْلُ alone reads "pregnancy"; فَازَ بِـ = won
  something; "dob" is a person's age, not a tree's; "notified" is too formal for family talk.
- A relation's `lemma` typed by hand (حَبَّة|حبب, shadda/vowel order) stops `fil pages` ("names what is not
  studied"): copy it from the catalogue keys (`nb._key(l)` over `noun_stage.catalogue`), NFC-matched.

- Batch 9 (2026-11-06, 9 re-plan rounds). Skipped participles/adjectives (حَلال، راحِم، رازِق، طاغي، عاد، غاوي، فَرِح،
  ظَهِير، مَيْتَة، مُنِير، واقِع، خاطِئ، خَصِيم، شارِب …), bare-accusative/idiom lemmas (خِلاف مِنْ خِلَافٍ، خِيفَة، فَرِيضَة،
  جَهْد جَهْدَ أَيْمَانِهِمْ، خَطْب مَا خَطْبُكُمْ، جَرَم، وَحْد) and رَشَد (variant of رُشْد). HELD_BACK: خَلاق، خُلْد، عُقْبَى، فاطِر،
  حاكِم (always الْحَاكِمِينَ = God), رَقِيب، مَقْت، مَرَدّ، وَحْى، وَعِيد، حَرِيق، تَقْدِير، تَفْصِيل، أَصْنام، and MSA-misleading
  سِيما (لَا سِيَّمَا)، طَرْف، عَرَض، كَرَّة (ball)، سُرُر (navels)، قَصَص (MSA plural of قِصَّة)، سَلَم (forward sale)، تَقَلُّب،
  أَسْباط، حَوارِيّ، حِجْر، مَنّ، وَقْر، سُجُود (merges ساجِد's plural). Run `att.py` on every new lemma in each re-plan round.
- Scratch helpers that paid off (rewrite each session, ~15 lines each): `skiphold.py skip L=reason … | hold L …`
  (NFC-matched to batch.txt), `att.py`, `gl.py` (CAMeL root:gloss), `tab.py --gaps` (batch table gaps), `ov.py tri()`.
  The Sonnet halves type keys with shadda/vowel swapped (ذَرَّة، ظُلَّة، فِضَّة، حَبَّة → "no case table"): remap their
  keys NFC → batch.txt before `paradigms`. zsh does not word-split `$VAR` — use `${=VAR}`.
- Glosses that failed → accepted: shone (لَمَعَ: use present يَلْمَعُ shines), تَجْرِي run (→ تَرْكُضُ), فارِس knight,
  مَخْزَن storehouse, عَرُوس bridegroom only, ثَوْب garment, لَبِسَ put on, الْأَرْض earth, حَرَام sin, بَرِّيّ land,
  سِنّ (age) fails, تَصَرَّفَ behaved, اسْتَعَدَّ got ready, مَنَعَ/نَهَى fail as prohibited (امْتَنَعَ عَنْ abstained),
  British "tranquillity" is the accepted spelling for سَكِينَة. Root exceptions added: wine خ.م.ر، grave ق.ب.ر،
  old age ك.ب.ر، town ب.ل.د، shelter ظ.ل.ل.
- Reviewer refusals: a gloss must carry the tense/number (انْتَظَرَ "waited for", خَافَ الطِّفْلُ "was afraid"); a verb's own
  preposition gets "-" or merges into the verb gloss (اقْتَرَبَ مِنْ، احْتَفَلَ بِـ); الْخُرُوج is "going out" (exit reads
  مَخْرَج); يَرْكَبُ عَلَى is colloquial (رَكِبَ takes an object).

- Batch 10 (2026-11-06, 6 re-plan rounds, 198 sentences, 7+1+1 refused in 4 rounds; وُسْع keeps only subject + preposition). Skipped ~45 participles/elatives (مُنزِل،
  مُهْلِك، مُسْتَضْعَف، أَرْحَم، أَقْوَم …), adverbs غَد، غُدُوّ، كَرْه (always غَدًا/بِالْغُدُوِّ/كَرْهًا), كافَّة، idioms بال، دابِر، دَأْب
  (كَدَأْبِ), feminines مُنافِقَة، صاحِبَة as "variant (on X's card)". HELD_BACK: شِرْك، مُشْرِكَة، مَرْضات، مِرْيَة، نَكِير، نُبُوَّة،
  نُشُور، بَعْث، انتِقام، أَكِنَّة، ثُبُور، حاصِب، رَجْفَة، قارِعَة، مَحِيص، حُور، خَزَنَت، داعِي، زُلْفَى، شَعائِر (God/Hell/unseen/
  revelation), عَلَقَة (MSA leech), أَحْبار (MSA inks), جِهاد، نِكاح (vulgar in dialect), دَعْوَى (lawsuit), صَعِيد (MSA level).
- Gloss-exception root keys use CAMeL's root, where a hollow wāw is `#` (فَوْج is ف.#.ج, لَوْح ل.#.ح): print `gl.py` BEFORE
  writing the exception. A possessive-only Quranic noun (مَكانَت، أَسْلِحَت) gets no sheet numbers until its whole row is
  documented — check `bs-sheet` numbers for `[]` before splitting. Failed → accepted: يَدُورُ goes around, بِهُدُوءٍ/بِبُطْءٍ
  (use an adjective: الْبَطِيء slow), الْإِنْسَان human being, يَحْتَفِظُ preserves, أَصَابَ afflicted, ارْتِفَاع (elevation),
  شِدَّة intensity, مَمْلُوء full, أَشْعَلَ ignited; تُؤْلِمُ، حَافَظَ، نَاقَشَ، اجْتَمَعَ (met)، شَكَّلَ fail.
- Reviewer refusals: سَقْف alone reads "ceiling" (a cat sits عَلَى السَّطْحِ); bare شَأْن is unnatural as an object or with
  تَفَاصِيل (أَصْحَاب glosses "owners" — use الشَّأْنُ الْعَامُّ "public affairs", and عَظِيمَة "great", not كَبِيرَة, for importance); هَذَا شَأْنٌ makes the noun a predicate, not a subject; وُسْع lives in فِي وُسْعِ / بَذَلَ وُسْعَهُ.

## Pilot lessons (2026-11-05, 50 nouns)
- 198 sentences drafted, 6 refused by the blind reviewer (3%), all repaired and approved.
- Form glosses: the composer skips what it cannot know — readings that differ, عَن, vocatives,
  emphatic la-, a bare accusative after إِنَّ/كَانَ, second plurals (عُيُون "springs" ≠ أَعْيُن "eyes").
