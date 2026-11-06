# Nijanse / Nuances — Quranic near-synonyms (plan and pilot, 2026-11-06)

Cards say what a word means, not *why this word and not another*. A nuance group gathers near-synonyms
(čovjek: إِنْسَان · بَشَر · رَجُل · اِمْرُؤ · نَاس) and says what they share, how each differs, and shows ayat
where the choice of word matters. Bosnian and English only, like nouns and adjectives.

## Sources and content rules
- Our own words, grounded in classical public-domain lexicography: ar-Rāġib al-Iṣfahānī, *Mufradāt alfāẓ
  al-Qurʾān*, and Abū Hilāl al-ʿAskarī, *al-Furūq al-luġawiyya*, cited by name per group. No modern
  edition's text or copyrighted translation is copied.
- A view one scholar holds is attributed to him; a tendency is stated as a tendency, with a counter-example
  when the Quran has one; contested tafsir readings are named in the ayah's note.
- A blind Sonnet reviewer checks every claim against the cited ayat (`fil nuances review-export`); its flags
  are resolved by softening, attributing or holding back, and each decision is written in the group's `notes`.

## How it is built
- Data: `data/nuance_groups.json`, one group per key (= page slug). Validated on load
  (`fil.nuances.model`, frozen dataclasses, `InvalidNuanceData`): ≥ 2 members, bs + en for every text,
  1–3 ayat per member, a member is a catalogue verb (`root_form`) or noun-catalogue lemmas (`lemma|root`,
  summed where the corpus splits one word).
- Gate (`fil.nuances.gate`, pure, behind a `Concordance` port; wired to the verb and noun catalogues in
  `fil.stages.nuances`): each member's count is the catalogue's; each cited ayah holds the member's word.
  It runs in the tests, in `fil nuances check`, and stops `fil pages`.
- Pages: `/bs/nijanse/`, `/en/nuances/` and `/<lang>/<folder>/<slug>/`, in the sitemap; "Nijanse/Nuances"
  in every top bar and the app (bs/en). Per word: Arabic with harakat and its checked synthetic voice,
  count, nuance, link to its verb/noun/adjective card when studied, ayat with the word marked and recited
  (QuranHive), the ayah streamed, the free translation (Pickthall; Bosnian pages fall back to English)
  and our bs/en note on why the word fits. Verb, noun and adjective pages of member words get
  "Slične riječi / Similar words".
- Next batches: the `/fil-nuances-batch` skill.

## Pilot (5 groups)
insan-bashar · jaa-ata · raa-nazara-absara · khawf-khashya · qalb-fuad-sadr. Held back after review:
al-ʿAskarī's خوف/خشية formulation (could not be verified here) and the attribution of the "breast vs heart"
saying to ar-Rāġib (now "it has been said").

## Batch 2 (25 groups, 30 in all)
Verbs: عَلِمَ/عَرَفَ · خَلَقَ/جَعَلَ/فَطَرَ · أَرْسَلَ/بَعَثَ · قَالَ/كَلَّمَ/نَطَقَ · سَمِعَ/اِسْتَمَعَ/أَنْصَتَ · أَنْزَلَ/نَزَّلَ · رَجَعَ/عَادَ ·
آتَى/وَهَبَ/أَعْطَى · فَعَلَ/عَمِلَ/صَنَعَ · أَكَلَ/طَعِمَ · ظَنَّ/حَسِبَ/زَعَمَ. Nouns and adjectives: حُزْن/أَسَف/غَمّ · فَرِحَ/سُرُور/مَسْرُور ·
كَذِب/إِفْك/زُور · ذَنْب/إِثْم/سَيِّئَة/خَطِيئَة · عَذَاب/عِقَاب · سَنَة/عَام · طَرِيق/سَبِيل/صِرَاط · بَيْت/دَار/مَسْكَن · نُور/ضِيَاء ·
مَطَر/غَيْث · عَيْن/بَصَر · كِتَاب/صُحُف · كَبِير/عَظِيم · حَمْد/شَكَرَ. Held back after review: ar-Rāġib's remark on سَنَة/عَام
in 29:14, the attribution of "ḍiyāʾ is stronger than nūr" to az-Zamaḫšarī (now unattributed tafsir), the
locus of the Ibn ʿAbbās fāṭir report, ar-Rāġib's "khaṭīʾa is mostly unintended" and al-ʿAskarī's entries
(not verifiable here).
