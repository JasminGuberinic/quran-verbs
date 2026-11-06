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
- Every claim in ar-Rāġib's name is checked against his text before review: the OpenITI corpus's
  *al-Mufradāt fī ġarīb al-Qurʾān*, version `0502RaghibIsbahani.Mufradat.JK001150-ara1` (ed. M. S. Kīlānī,
  Dār al-Maʿrifa; OpenITI 0525AH repository on GitHub). The OpenITI corpus is released under **CC BY-NC-SA
  4.0** (Zenodo, doi:10.5281/zenodo.3082464). We use it for verification only: it is downloaded into the
  gitignored `build/openiti-mufradat/`, never committed, and none of its text reaches a page — our
  explanations are our own words. `fil nuances mufradat ROOT…` / `--mentions WORD` (fil.nuances.mufradat)
  prints the entries; each group records what was read in `verified` (source + headwords) and in a note, and
  the gate refuses a group that names ar-Rāġib without that record.
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

## Batch 3 (25 groups, 55 in all)
Verbs: آمَنَ/أَسْلَمَ/أَيْقَنَ · دَعَا/نَادَى · مَاتَ/تَوَفَّى · سَأَلَ/اِسْتَفْتَى · أَمَرَ/وَصَّى · نَهَى/حَرَّمَ · تَرَكَ/وَذَرَ · جَمَعَ/حَشَرَ ·
أَهْلَكَ/دَمَّرَ · كَسَبَ/اِكْتَسَبَ · غَفَرَ/عَفَا/كَفَّرَ · تَابَ/أَنَابَ. Nouns and adjectives: رَحْمٰن/رَحِيم/رَءُوف · كَفَرَ/مُشْرِك/مُنَافِق ·
هُدًى/رُشْد · ضَلَال/غَيّ · ظُلْم/بَغْي/عُدْوَان · عَدْل/قِسْط · جَزَاء/أَجْر/ثَوَاب · نَار/جَحِيم/سَعِير · قَرْيَة/مَدِينَة · فَقِير/مِسْكِين ·
وَلِيّ/نَصِير · شَكّ/رَيْب · أَب/وَالِد. Held back after review: the claim that ar-Rāġib cites 9:128 for raḥīm, ar-Rāġib's own
wording on rayb (now tafsir on 2:2), "Form VIII stresses effort" as his (now "many mufassirun", with the dissent),
and al-ʿAskarī throughout. Not built: a Paradise-names group (فِرْدَوْس, عَدْن and جَهَنَّم are outside the noun
catalogue). The faqīr/miskīn dispute is shown with both sides' proof ayat, neither chosen.

## Batch 4 (25 groups, 80 in all)
Acts of worship: صَلَاة/دُعَاء · زَكَاة/صَدَقَة/أَنْفَقَ · صِيَام/صَوْم/صَامَ · حَجّ/عُمْرَة. Speech acts and the mind: أَقْسَمَ/حَلَفَ ·
نَبَأ/خَبَر · جَادَلَ/حَاجَّ/اخْتَصَمَ · تَفَكَّرَ/تَدَبَّرَ/عَقَلَ/فَقِهَ · اصْطَفَى/اجْتَبَى/اخْتَارَ. Motion and body: مَشَى/سَارَ/سَعَى ·
مَسَّ/لَمَسَ · جِسْم/جَسَد/بَدَن. Emotions and states: غَضَب/غَيْظ/سَخَط · أَحَبَّ/وَدَّ/مَوَدَّة · رَجَا/طَمِعَ ·
اسْتَكْبَرَ/تَكَبَّرَ/مُتَكَبِّر · خَاشِع/تَضَرُّع/خَاضِع · اطْمَأَنَّ/سَكِينَة · فِتْنَة/بَلَاء/ابْتَلَى. Nature, time, people:
بَحْر/يَمّ · سَحَاب/غَمَام/مُزْن · فَجْر/صُبْح/ضُحًى · أَجَل/مِيقَات/وَقْت · أَهْل/آل · صَاحِب/خَلِيل/صَدِيق. Held back after
review: ar-Rāġib's wording on saḵaṭ, ḫuḍūʿ, muzn and ṣadīq (not verifiable here), "draw near" for iǧtibāʾ (not his),
"lifeless" as a rule for جَسَد, the loanword claim for يَمّ, and al-ʿAskarī throughout. Not cited because tafsir differs
widely: 2:210, 7:203, 38:34, 42:23, 71:13 and the لَامَسْتُم ayat (4:43, 5:6).

## ar-Rāġib verified against the Mufradāt (80 groups, 2026-11-06)
All 80 groups' ar-Rāġib claims (and the few given to az-Zamaḫšarī / al-ʿAskarī) were checked against the
OpenITI text, entry by entry, by four parallel verifiers with every quote machine-checked against the text.
552 attributed points: 498 confirmed, 39 partial, 3 different, 12 not checkable here (other authors), 0 not
found. 59 texts changed: 34 reworded to what he says, 5 re-attributed (Quranic usage, or from an unverifiable
author to ar-Rāġib where he says the same), 2 dropped (the al-Kaššāf and al-Furūq source lines), 18 improved
where his entry says more than we had. 78 groups carry a `verified` record (faqir-miskin and matar-ghayth
name no lexicographer). Notable corrections: the inzāl/tanzīl contrast is his only for the Quran and the
angels; ityān may be said of the intent to come (not "on its way"); faraḥ "mostly bodily" (not "worldly"),
allowed in his reading only in 10:58 and 30:4; zakāh from growth/blessing (not "purifies the soul"); tawaffī
"taking in full" is his definition of istīfāʾ; ab for grandfather/uncle only when named with the father; the
three kinds of ẓulm and the "breast" saying are quoted by him from "some sages"; nifāq from nafaq, a tunnel
through (not "two openings"); naẓar "look and not see" is his (al-ʿAskarī no longer cited); the 6:1 note
gives his reading of خلق/جعل instead of az-Zamaḫšarī's (al-Kaššāf could not be checked). Recovered from
"held back": ḵaṭīʾa mostly unintended, 9:128 for raḥīm, 29:14 sana/ʿām, saḵaṭ, muzn, ḫuḍūʿ, ṣadāqa.

## Review of the verification pass, and sources as the book spells them (2026-11-06)
The 59 texts changed by the verification were given to a blind reviewer (who could read the cited entries):
36 claims, 16 flagged, 15 fixed (99:7 "uradio" kept: Korkut's wording). Notable: 23:4 now shows ar-Rāġib's own
reading (lām of purpose) beside most mufassirun's; ḍiyāʾ is his "more specific", not "stronger"; ijtibāʾ "with
hudā" only for Adam and Abraham; the "ransom" in 2:48 is the mufassirun's, not his; قَرْيَة is "town / naselje"
throughout, keeping "city / grad" for مَدِينَة. Every `sources` line now names the Mufradāt entries as the book
spells them (أبا the father, not أب the pasture; شكك, جاء, سرر, بلى …), and every entry it names is in `verified`
— the gate now refuses a cited entry the record does not list. Twelve cited-but-unlisted entries were read and
added (consistent; no attributed point rests on them alone).

## Batch 5 (25 groups, 105 in all)
Mostly pairs ar-Rāġib himself sets side by side (`fil nuances mufradat --mentions WORD`): أَرَادَ/شَاءَ · حَكَمَ/قَضَى ·
نَسِيَ/غَافِل · ضَحِكَ/تَبَسَّمَ · كَتَمَ/أَخْفَى/أَسَرَّ · أَعْرَضَ/تَوَلَّى · نَوْم/سِنَة/نُعَاس/رُقُود · وَلَد/ابْن · مَرَض/مَرِيض/سَقِيم ·
دَخَلَ/وَلَجَ · خَتَمَ/طَبَعَ · وَهَنَ/ضَعِيف · أُمَّة/قَوْم · رَسُول/نَبِيّ · فَاحِشَة/مُنكَر · بِرّ/إِحْسَان · ضُرّ/أَذًى · ذِلَّة/ذُلّ/خِزْي ·
رُؤْيَا/حُلُم · قَتَلَ/ذَبَحَ · عَهْد/مِيثَاق · سَاحِر/كَاهِن/شَاعِر · جَاهِل/سَفِيه · عَجِلَ/اسْتَعْجَلَ/سَارَعَ · فَوْز/أَفْلَحَ.
Verification first (three verifiers, quotes machine-checked): 380 points, 344 confirmed, 35 partial, 1 different
(Moses called sāḥir in the sense of illusion, not of transformation); 34 texts changed. Then the blind review:
82 claims, 42 flagged, 75 fixes, all in the texts (none held back). Left out on purpose: the "rasūl brings a new
law" distinction (not ar-Rāġib's; scholars differ), 2:213 and 2:124 (tafsir differs), 42:24 and 80:1 (said to the
Prophet), 20:115 (nasiya there is read two ways). ذبح and وثق open with no heading mark in the OpenITI
text; the parser now lists them by their opening words (fil.nuances.mufradat), so they are entries of their own.

## Batch 6 (25 groups, 130 in all)
Showing and hiding, people and groups: أَبْدَى/أَظْهَرَ/أَعْلَنَ · حِزْب/فَرِيق/طَائِفَة/شِيعَة. Gifts, power, worship: نِعْمَة/فَضْل ·
مُلْك/سُلْطَان · عَبَدَ/أَطَاعَ · بَخِلَ/بُخْل/شُحّ. Good, evil, truth: شَرّ/سُوء · خَيْر/حَسَنَة · حَقّ/صِدْق. Revelation and its
recitation: تَلَا/قَرَأَ/رَتَّلَ · بَيَّنَ/فَصَّلَ · سَجَدَ/رَكَعَ. Purity: طَهَّرَ/زَكَّى · رِجْس/نَجَس. Creation of man: تُرَاب/طِين/صَلْصَال/حَمَأ.
Presence, hindrance, counting: شَهِدَ/حَضَرَ · صَدَّ/مَنَعَ · أَحْصَى/عَدَّ. This world: لَهْو/لَعِب · زِينَة/زُخْرُف · كَيْد/مَكْر ·
ضَاقَ/حَرَج · رَجْفَة/صَيْحَة/صَاعِقَة · رَمَى/قَذَفَ · وِزْر/ثَقَل. Drafted from the Mufradāt entries, then verified (463 points:
435 confirmed, 27 partial, 1 not found; 28 texts changed, quotes machine-checked), then reviewed blind (83 claims,
49 flagged, every flag fixed in the texts, none held back). Allah's كَيْد and مَكْر are given only with a gloss and
"as befits Him": respite (7:183, ar-Rāġib's) and requital (27:50, the mufassirun's), no fixed split between them.
Left out on purpose: 69:29 (سُلْطَان there is power or proof, he gives both), 18:86 حَمِئَة, 74:4 and 2:125 as
طَهَّرَ ayat (readings differ), 73:20 (lan tuḥṣūhu read two ways), 21:17 and 31:6 لَهْو (tafsir differs), 7:2 and
6:125 حَرَج, 86:15–16 and 7:99, 2:34, 38:24, 94:2, and 28:87, 20:16, 2:147 (said to the Prophet). 107:7 al-māʿūn is
cited only for his "opposite of giving", its meaning left open. Not built yet: particle groups (لَنْ/لَا, إِنْ/إِذَا) —
members are verbs or noun lemmas only.

## Batch 7 (25 groups, 155 in all)
Restraint and loss: صَبْر/حَلِيم/كَاظِم · خَسِرَ/خَابَ · حَبِطَ/أَبْطَلَ · حَذِرَ/مُشْفِق/وَجِلَ · حَسْرَة/نَادِم. Signs, mind, religion:
آيَة/بُرْهَان/بَيِّنَة/حُجَّة · أَلْبَاب/نُهَى · نَفْس/رُوح · دِين/مِلَّة/شِرْعَة · هَوًى/شَهْوَة · وَعَظَ/نَصَحَ · أَتَمَّ/أَكْمَلَ. Fear:
رُعْب/فَزَع/رَوْع. The earth and its gifts: ثَمَرَة/فَاكِهَة · حَرْث/زَرْع · سَقَى/أَسْقَى · رِزْق/مَتَاع · جَبَل/رَوَاسِي · فُلْك/سَفِينَة ·
كَأْس/أَكْوَاب/أَبَارِيق · قَبْر/أَجْدَاث. Hands and people: قَبَضَ/أَمْسَكَ · بَسَطَ/مَدَّ · زَوْج/بَعْل · فَاسِق/فَاجِر/عَصَى.
Drafted from the Mufradāt entries, verified (513 points: 477 confirmed, 34 partial, 2 not found; 33 texts changed,
quotes machine-checked), reviewed blind (83 claims, 39 flagged, every flag fixed in the texts, none held back).
Allah's ḥilm, nafs, qabḍ/basṭ and imsāk carry "as befits Him"; 17:85 leaves the rūḥ's reality with Allah and says
the mufassirun differ; Paradise vessels and fruit only as the ayat give them. Left out on purpose: 49:2 (scope of the
warning differs), 12:24, 2:124, 2:256 (he gives two readings), 2:223, 4:34, 56:82, 20:121 (Adam), 39:65 and 6:88
(conditionals about prophets), and 9:84, 5:41, 5:49, 33:37, 15:88, 20:131, 35:8 (said to the Prophet). Counts that
include another sense are noted per group (دِين with yawm ad-dīn, بَعْل with the idol Baʿl, هَوَاء with 14:43);
حِجْر (intellect only in 89:5) and rīḥ/riyāḥ (one lemma in the corpus) were not built. The new Bosnian texts spell
Paradise Džennet throughout.
