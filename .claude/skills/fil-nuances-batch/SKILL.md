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
   replacements or json), never paste it whole into the conversation.
4. `fil nuances check` → prints only problems + one summary line: a count that is not the catalogue's, a
   cited ayah that does not hold the word, an unknown lemma. Fix until 0 problems. (The tests run the same
   gate; `fil pages` refuses to build otherwise.)
5. `fil nuances review-export` → build/nuances/blind.json (claims en+bs with the ayat's Arabic and
   Pickthall). Give it to a FRESH Sonnet general-purpose agent as a blind reviewer: check each nuance against
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
