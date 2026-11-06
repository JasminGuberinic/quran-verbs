---
name: fil-nuances-batch
description: Add the next batch of Quranic near-synonym groups ("Nijanse / Nuances": what the words share, how each differs, illustrating ayat) to the Fiʿl study site, mechanically and token-efficiently. Use when the user says "/fil-nuances-batch", "next nuances", "dodaj još nijansi", or asks to add near-synonym groups.
---

# Add a batch of nuance groups (bs + en)

Goal: groups of Quranic near-synonyms — why this word and not another (docs/NUANCES-PLAN.md). One batch
(~20–50 groups) per conversation. Rules as everywhere: bs + en only, never ask the owner linguistic
questions (decide, write the decision in the group's `notes`), commit and push to study-site (never main,
never deploy). Engine: src/fil/nuances/ (pure: model, gate), stage src/fil/stages/nuances.py (CLI, the
corpus Concordance), cards fil.stages.nuance_site, pages fil.stages.nuance_pages + fil.pages.nuance_render.

## Content rules (sacred)
- Explanations in our own words, grounded in classical public-domain lexicography: ar-Rāġib al-Iṣfahānī,
  *Mufradāt alfāẓ al-Qurʾān*, and Abū Hilāl al-ʿAskarī, *al-Furūq al-luġawiyya*. Name the works (and the
  entries) in `sources`. Never copy a modern edition's text or a modern copyrighted translation.
- Attribute what is one scholar's view ("Prema ar-Rāġibu…", "According to ar-Rāġib…"); state a tendency as a
  tendency ("najčešće", "often") and, where the Quran has a counter-example, show it (خَشْيَةَ إِمْلَاقٍ 17:31).
  Do not attribute what you cannot vouch for to al-ʿAskarī — hold it back and note it (pilot: his خوف/خشية
  wording was held back).
- Our own observation of Quranic usage is said as such, not put in a lexicographer's mouth.
- Where tafsir differs on an ayah, say so in the `why` (7:198: idols or idolaters; 28:10 فارغًا).
- Bosnian follows Korkut's conventions (Allah, ajet, Kur'an, Poslanik, Musa, Ibrahim, Jusuf, dženet);
  English Sahih International style. Content policy: respectful of God and the prophets, no depictions.
  شَرَحَ صَدْرَهُ is "proširiti/širiti grudi", not "otvoriti".

## Working in an agent worktree
- The worktree has no corpus: symlink `data/qac`, `data/quranhive`, `data/translations` to the main repo's;
  copy (do not link) `build/nouns/*.tsv`; link the main repo's `build/{speech,recitation,compressed}-cache`.
- The venv's editable install points at the main repo's src: run `PYTHONPATH=src
  ~/Development/quran-verbs/.venv/bin/python -m fil.cli …` and `… -m pytest -q`.
- Keep scratch scripts in `build/scratch/` (gitignored): the isolation guard refuses files outside the worktree
  and Python that mentions git — save `git show HEAD:data/nuance_groups.json` to a file first.

## Steps
1. Pick the groups (classic pairs from al-Furūq; frequent Quranic words first). A word may sit in more than
   one group; its card then links every group.
2. For each member find its corpus identity and count with the catalogues — never hand-count:
   - verb: `"verb": "root_form"` (Form I أَتَى is `أتي_1`; Form IV آتَى is a different verb);
   - noun/adjective: `"lemmas": ["lemma|root", …]` exactly as build/nouns/catalogue.tsv (`fil nouns catalogue`)
     writes them. Sum lemmas the corpus splits (broken plural رِجال beside رَجُل; امْرِئ, مَرْء, امْرُؤٌا, امْرَأ)
     and say so in `notes`.
3. Write the groups into data/nuance_groups.json (one group per key = page slug, lowercase latin, e.g.
   `qalb-fuad-sadr`): `title`, `shared`, `tellApart` (one line, Arabic inline), `sources`, `notes`, `members`
   (each: `arabic` with harakat, `verb` or `lemmas`, `count`, `meaning`, `nuance`, 1–3 `ayat` of
   `{"ref": "s:a", "why": {bs, en}}`). Every text has bs and en. Edit the file with a script (string
   replacements or json), never paste it whole into the conversation. Mechanics that save a round trip:
   - Write the content as Python in build/scratch (helpers `T(bs,en)`, `A(ref,bs,en)`, `M(...)`, `G(...)`), then
     a merge script: start from HEAD's file, add the groups, fill every `count` from
     `CatalogueConcordance.from_corpus().attestation(member.corpus)` (a placeholder must be ≥ 1 to parse), and
     write the file back in its layout — one-space indent, with `lemmas`, ayah items and `{bs,en}` texts of
     ≤ 120 characters on one line. A dumper with those three rules round-trips the file byte for byte; plain
     `json.dumps(indent=…)` rewrites every earlier line.
   - Copy lemma keys from catalogue.tsv byte for byte: mark order differs (سَيِّئَة is filed with shadda before
     kasra), and a hand-typed key is "not a word of the corpus".
   - Before writing "always / never / only" about Quranic usage, list the member's places
     (`fil.stages.nouns.load_occurrences()` / `service.form_occurrences()` with the ayah text) and read them all.
   - tests/test_nuances.py pins the number of stored groups: update it with the batch.
4. `fil nuances check` → prints only problems + one summary line: a count that is not the catalogue's, a
   cited ayah that does not hold the word, an unknown lemma. Fix until 0 problems. (The tests run the same
   gate; `fil pages` refuses to build otherwise.)
5. `fil nuances review-export` → build/nuances/blind.json (claims en+bs with the ayat's Arabic and
   Pickthall; filter it to the new groups' ids — earlier batches are already reviewed). Give it to a FRESH Sonnet general-purpose agent as a blind reviewer: check each nuance against
   the cited ayat and the two lexicographers, flag misattributions, contested readings, bs/en drift, Korkut
   style, content policy; OK or FLAG + suggested rewording per claim id. Apply the flags (soften, attribute,
   or hold back and note), re-run `check`.
6. `fil pages` (log to a file; headwords are voiced by the checked synthetic voice — a disagreement stops the
   build: give the member a `spoken` form the readers agree on — a pausal tāʾ marbūṭa خَشْيَة is said
   خَشْيَةٌ — or fix fil.speech), `pytest -q`, commit, push.

## Pilot (2026-11-06): 5 groups
insan-bashar (إِنْسَان بَشَر رَجُل اِمْرُؤ نَاس) · jaa-ata (جَاءَ أَتَى) · raa-nazara-absara (رَأَى نَظَرَ أَبْصَرَ)
· khawf-khashya (خَوْف خَشْيَة) · qalb-fuad-sadr (قَلْب فُؤَاد صَدْر). Ayah translations are the site's free
ones (Pickthall; Bosnian pages fall back to English — no free Bosnian translation exists); our `why` line is
bs + en.

## Batch 2 (2026-11-06): 25 groups → 30
alima-arafa · khalaqa-jaala-fatara · arsala-baatha · qala-kallama-nataqa · samia-istamaa-ansata · anzala-nazzala
· rajaa-ada · ata-ata-wahaba · faala-amila-sanaa · akala-taima · huzn-asaf-ghamm · farah-surur · kadhib-ifk-zur
· dhanb-ithm-sayyia-khatia · adhab-iqab · sana-am · tariq-sabil-sirat · bayt-dar-maskan · nur-diya · matar-ghayth
· ayn-basar · kitab-suhuf · kabir-azim · hamd-shukr · zanna-hasiba-zaama. Lessons:
- Check a candidate exists before writing it: جَلَسَ (no verb in the corpus), آبَ (only مَآب), بَرَأَ (1×),
  كَفّ (filed as كَفَّي, 2×) and دَانٍ were dropped for that reason.
- Ground claims you are sure of in ar-Rāġib; when a classic distinction is really a later scholar's or a
  modern one (آتَى/أَعْطَى by revocability; أَمْطَرَ for punishment), leave it out and say so in `notes`.
  A group may rest on "Quranic usage — our own observation" (matar-ghayth) if every use is listed and read.
- What the reviewer flagged most: a lexicographer's tendency of the language stated as Quranic usage (سَنَة
  "hardship" — the Quran's سَنَة is mostly neutral); "only/always" where a counter-example exists (فَرِحَ
  approved in 3:170 too; the noun عِقَاب is always Allah's, the verb عَاقَبَ is not; شُكْر "only for a
  favour" vs Allah as شَاكِر); a tafsir line pinned to a named mufassir it may not be in (ضِيَاء "stronger"
  as az-Zamaḫšarī's → "tafsir often explains"); and ayat about Allah that need the tafsir gloss beside them
  (24:35 light, 43:55 anger). Write those safeguards in the first draft.
- Giving tāʾ-marbūṭa headwords `spoken` up front (سَيِّئَةٌ, خَطِيئَةٌ, سَنَةٌ) let `fil pages` pass first time.

## Batch 3 (2026-11-06): 25 groups → 55
rahman-rahim-rauf · kafara-mushrik-munafiq · amana-aslama-ayqana · daa-nada · huda-rushd · dalal-ghayy
· zulm-baghy-udwan · adl-qist · jaza-ajr-thawab · nar-jahim-sair · qarya-madina · mata-tawaffa · saala-istafta
· amara-wassa · naha-harrama · taraka-wadhara · jamaa-hashara · ahlaka-dammara · kasaba-iktasaba · faqir-miskin
· wali-nasir · shakk-rayb · ghafara-afa-kaffara · taba-anaba · ab-walid. Lessons:
- Check the catalogue before planning a group: جَهَنَّم, فِرْدَوْس, عَدْن are proper names outside the noun catalogue
  (so no Paradise-names group; Hell is نَار/جَحِيم/سَعِير); رَأْفَة is 2× (use the adjective رَءُوف); the corpus
  splits وَالِد / وَالِدَي and أَب / آبَاء / أَبَوَان, رُشْد / رَشَد, مَدِينَة / مَدَائِن — sum and note.
- Let the merge script resolve lemma keys against catalogue.tsv by (root, consonant skeleton) and fail on
  ambiguity: no hand-typed key reached the file, and `check` passed first time.
- A member ayah must hold the member's own lemma: a verb member cannot be illustrated by an ayah with only
  its verbal noun (دَعَا with 2:171 دُعَاءً وَنِدَاءً) — `check` catches it, but pick right in the draft.
- A `build/scratch/forms.py` listing (service.form_occurrences with tense/pronoun/passive) settles
  grammar claims fast: وَذَرَ never in the past (45/45), أَنَابَ never with Allah as subject, تَوَفَّى's subject
  always Allah / angels / death or passive.
- What the reviewers flagged most this time: a later tafsir point put under ar-Rāġib's name (iktasaba
  "stresses effort"); "tafsir says" where it is "many / some mufassirun"; a definition that takes one side of a
  named dispute (faqīr/miskīn tellApart); conditionals about the Prophet (10:94) and ayat about forgiveness
  (39:53 with 4:48) that need the majority reading beside them; bs/en drift inside quoted ayat (Korkut vs
  Sahih wording, e.g. 6:60 "uspavljuje" vs "takes your souls"); and ayat cited for what the next ayah says
  (96:9 vs 96:10, 20:59 vs 20:60). "bijednik" is pejorative for مِسْكِين: use "nevoljnik, potrebit".
- بَغْي needed `spoken` بَغْيٌ (a final yāʾ with sukūn, like the tāʾ marbūṭa cases).
