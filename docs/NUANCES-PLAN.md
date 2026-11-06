# Nijanse / Nuances — Quranic near-synonyms (plan and pilot, 2026-11-06)

Cards say what a word means, not *why this word and not another*. A nuance group gathers near-synonyms
(čovjek: إِنْسَان · بَشَر · رَجُل · اِمْرُؤ · نَاس) and says what they share, how each differs, and shows ayat
where the choice of word matters. Bosnian and English only, like nouns and adjectives.

## Sources and content rules
- Our own words, grounded in classical public-domain lexicography: ar-Rāġib al-Iṣfahānī, *Mufradāt alfāẓ
  al-Qurʾān*, and Abū Hilāl al-ʿAskarī, *al-Furūq al-luġawiyya*, cited by name per group. No modern
  edition's text or copyrighted translation is copied.
- Ayah quotations: Sahih International / Korkut are terminology and style references only; never quote or closely
  paraphrase their ayah translations; ayah quotes in en come only from the shipped Pickthall text; bs ayah quotes are
  our own translation. Double marks quote an ayah and name it, glosses take single ones, and a group with Bosnian
  quotes declares `"ayahQuotes": {"bs": "own"}` — fil.ayah_quotes fails the tests and `fil nuances check` otherwise.
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

## Bosnian spelling of Paradise and Hell (2026-11-06)
Korkut writes Džennet and Džehennem (capitalised, double n), adjectives lowercase (džennetske bašče). The texts had
drifted (Dženet, dženet, dženneta, džehennem, dženetske — 25 places in data/nuance_groups.json); all are unified, and
tests/test_bosnian_spelling.py fails on any other spelling in data/ or the site sources.

## Batch 8 (25 groups, 180 in all)
Motion: هَبَطَ/نَزَلَ · عَرَجَ/صَعِدَ/رَقِيَ · خَرَجَ/بَرَزَ · ذَهَبَ/مَضَى. Trade, intent, keeping, strength: اشْتَرَى/شَرَى/بَيْع/تِجَارَة ·
هَمَّ/عَزَمَ · حَفِظَ/رَعَى · قُوَّة/بَأْس/بَطْش · اسْتَطَاعَ/قَدَرَ/طَاقَة · وَجَدَ/أَلْفَى · كَرِهَ/أَبَى · نَزَعَ/خَطِفَ/سَلَبَ. Times of day:
عَشِيّ/أَصِيل · بُكْرَة/غُدُوّ. Shaping: صَوَّرَ/سَوَّى/قَدَّرَ. Hearts: عَدَاوَة/بَغْضَاء · حَسَدَ/غِلّ. Hunger and fatigue:
جُوع/مَخْمَصَة/مَسْغَبَة · نَصَب/لُغُوب. Kin and children: عَشِيرَة/رَهْط/فَصِيلَة · ذُرِّيَّة/نَسْل · طِفْل/صَبِيّ/غُلَام. Animals and
light: نَاقَة/جَمَل/إِبِل/بَعِير · دَابَّة/أَنْعَام/بَهِيمَة · سِرَاج/مِصْبَاح. Drafted from the Mufradāt entries, verified (437 points:
414 confirmed, 17 partial, 3 different, 3 not found; 23 texts changed, quotes machine-checked), reviewed blind (88 claims,
26 flagged, every flag fixed in the texts, none held back). Allah's ascent-to-Him (70:4), baṭš (44:16), qudra, taṣwīr
and taswiya carry "as befits Him"; 12:20 says only that Joseph is sold (who sold him is disputed). Left out on purpose:
Adam's descent ayat (2:36, 2:38, 7:24, 20:123 — ar-Rāġib's "belittlement" reading of hubūṭ is not put on a prophet),
12:24, 20:115, 2:34 / 15:31 / 20:116 (Iblīs, as in batch 6), 7:27, 33:72 (amāna read many ways), 27:82 (the dābba),
27:48, 2:124, 91:7 (he argues against one reading), 15:29 and 32:9 (lead into the rūḥ), 24:31, 18:74 and 18:80, 77:33
(camels or ropes), 25:61, 6:125, 4:34, 13:11, and 4:113, 35:8, 6:52, 18:28, 9:42 (said to or about the Prophet). Counts
that include another sense are noted per group (غِلّ with aġlāl "fetters", قَدَرَ with "straiten / measure", عَشِيّ
summed with عَشِيَّة); نَاقَة has no Mufradāt entry and rests on Quranic usage (all seven places read).

## Licence fix: ayah quotations (2026-11-06)
Earlier batches quoted ayat in English in Sahih International's wording and in Bosnian "in Korkut's wording from
memory" — both under copyright. Every quotation in data/nuance_groups.json, particles.json and pronouns.json was
rewritten: en quotes are now Pickthall's shipped text word for word (nuances 1,091, particles 270, pronouns 50; about
two dozen became our own unquoted paraphrase where his reading does not serve the point), bs quotes our own
translation from the Arabic (1,100 / 274 / 50; the ones that came out identical to the old text were translated
again, only a few short literal formulas remain), and several hundred glosses that sat in double quotes moved to single ones.
Reviewer notes that quoted Sahih/Korkut phrases were cut to single terms. The gate fil.ayah_quotes
(tests/test_ayah_quotes.py, `fil nuances|particles|pronouns check`) keeps it so.

## Batch 9 (25 groups, 205 in all)
The first batch written under the ayah-quotation rule from the start. Denying and mocking: كَذَّبَ/جَحَدَ/أَنْكَرَ · سَخِرَ/اسْتَهْزَأَ.
Allah's acts (each "as befits Him"): بَدَأَ/أَنْشَأَ/بَدِيع · نَجَّى/أَنْجَى/أَنْقَذَ · كَتَبَ/فَرَضَ · وَعْد/وَعِيد · سَبَّحَ/قَدَّسَ · أَنْظَرَ/أَمْلَى/مَهَّلَ.
Overstepping and excess: طَغَى/عَتَا · أَسْرَفَ/بَذَّرَ · بَدَّلَ/غَيَّرَ/حَرَّفَ · زَادَ/ضَاعَفَ. Staying and waiting: لَبِثَ/مَكَثَ ·
اِنْتَظَرَ/تَرَبَّصَ. Knowing and following: فَقِهَ/شَعَرَ · أَطَاعَ/اِتَّبَعَ. Things and places: جَنَّة/حَدَائِق/رَوْضَة · لِبَاس/ثِيَاب/سَرَابِيل ·
حَجَر/صَخْرَة · أَمْن/سَلَام · أَصْنَام/أَوْثَان/تَمَاثِيل · قَصْر/صَرْح · قَسَا/غَلِيظ/فَظّ · قِتَال/حَرْب · حَلَال/طَيِّب. English quotes are
Pickthall's words (checked per drafter with the gate before merging), Bosnian quotes our own translation; where Pickthall
gives two members one English word ("change" for بَدَّلَ/غَيَّرَ/حَرَّفَ, "lofty tower" for قَصْر and صَرْح, "rock" for حَجَر),
the ayah is paraphrased without quotation marks or the member named in [brackets]. Verified (446 points: 418 confirmed,
26 partial, 2 different; 23 texts changed — mostly verse numbers in notes: his wording is 36:40 not 21:33, 8:37 not 3:179,
20:40 not 26:18, 10:102 not 10:20), reviewed blind (84 claims, 41 flagged, every flag fixed in the texts; twelve Bosnian
quotes the reviewer found close to Korkut's sentences were translated again). Counts summed and noted: حِجَارَة + حَجَر,
صَخْرَة + صَخْر, أَمْن + أَمَنَة, غَلِيظ + غِلْظَة, طَيِّب + طَيِّبَات; كَتَبَ and أَمْلَى include 'write' / 'dictate'. Left out on purpose: 39:19,
33:38, 33:50, 66:2, 28:85, 11:112, 25:10, 5:41, 32:30, 8:65, 74:4 as an illustration (named only with his two readings),
53:17 (said to or about the Prophet), 18:80, 10:92, 33:33, 2:35 / 7:19 (which garden), 14:35, 77:32 as an illustration,
66:6, 39:53 (needs 4:48 beside it), 7:14 / 15:36 / 38:79 (Iblīs), 47:25, 4:119, 25:70, 33:30, 2:10 as an illustration,
49:2.

## Batch 10 (25 groups, 230 in all)
Help, trust, refuge, covenants: نَصَرَ/أَمَدَّ/أَعَانَ · تَوَكَّلَ/فَوَّضَ · عَاذَ/اعْتَصَمَ/مَلْجَأ · نَقَضَ/نَكَثَ. Acts: أَفْسَدَ/عَثَا · مَنَّ/أَنْعَمَ ·
أَعَدَّ/هَيَّأَ · قَامَ/وَقَفَ · خَرَّ/هَوَى/سَقَطَ · انْشَقَّ/انْفَطَرَ/انْفَلَقَ. Speech: كَلِمَة/قَوْل/حَدِيث · لَغْو/بَاطِل · سِرّ/نَجْوَى. Allah's Names and
witnesses (each "as befits Him"): عَلِيم/خَبِير · شَهِيد/رَقِيب/حَفِيظ · مِثْل/أَنْدَاد/كُفُو. Qualities: يَسِير/هَيِّن · جَمِيل/حَسَن. Things and
time: نَجْم/كَوْكَب/شِهَاب · فِرَاش/مِهَاد/بِسَاط · سُرُر/أَرَائِك · عُنُق/رَقَبَة · خَالِد/خُلْد/أَبَدًا · حِجَاب/غِطَاء/أَكِنَّة/غِشَاوَة · حِين/دَهْر/أَمَد.
Drafted from the Mufradāt entries, verified (440 points: 412 confirmed, 23 partial, 4 different, 1 not found; 27 texts changed —
mostly verse numbers in notes and one gloss we had widened), reviewed blind (88 claims, 29 flagged, every flag fixed in the
texts, none held back; nineteen Bosnian quotes the reviewers found close to Korkut's sentences were translated again).
English quotes are Pickthall's words; where he gives two members one English word ("help", "break", "refuge", "couches",
"veil", "covering") the ayah is paraphrased or the member named in [brackets]. مَلْجَأ has no Mufradāt entry and rests on Quranic usage (all three places read); thin members kept as
well-known pairs: فَوَّضَ, بِسَاط, اِنْفَطَرَ, اِنْفَلَقَ, كُفُو (1× each), هَيَّأَ (2×). Counts summed and noted: كَلِمَة + كَلِم, شِهَاب +
شُهُب, هَيِّن + أَهْوَن; هَوَى includes 'to desire', حَفِيظ includes حَفَظَة, حِين includes حِينَئِذٍ. مَهْد (cradle) was left out of the
bed group. Left out on purpose: 3:159, 33:37, 74:6, 9:84, 9:108, 73:2, 74:2, 4:80, 6:107, 42:48, 73:10, 33:28, 72:25 (said to or
by the Prophet), 26:22, 18:14, 66:3, 31:6, 2:37, 14:25, 38:32, 26:4 and 53:1 as illustrations, 53:1 / 55:6 / 56:75 / 86:3
(several readings), 6:76, 12:4, 37:88, 56:34, 12:100, 38:24, 7:143, 8:12, 47:4, 38:33, 4:14, 4:93, 20:120, 2:36, 7:24, 11:47,
20:37, 33:53, 17:45; 48:10 is paraphrased, not quoted.

## Batch 11 (25 groups, 255 in all) — the planned set is complete
The planned final batch. Allah's Names (each "as befits Him"): وَاحِد/أَحَد · مَلِك/مَالِك/مَلِيك · غَفُور/غَفَّار/عَفُوّ · قَدِير/قَادِر/مُقْتَدِر ·
خَالِق/بَارِئ/مُصَوِّر. The unseen and the Day: سَاعَة/قِيَامَة/قَارِعَة/حَاقَّة · جِنّ/جَانّ/جِنَّة. Reminding and sight: ذِكْر/ذِكْرَى/تَذْكِرَة ·
أَعْمَى/أَكْمَه. The body: سَمْع/أُذُن · رِجْل/قَدَم. Acts: أَلْقَى/نَبَذَ/طَرَحَ · تَفَرَّقَ/اخْتَلَفَ · قَدَّمَ/أَسْلَفَ · اِبْتَغَى/طَلَبَ · هَجَرَ/هَاجَرَ/اِعْتَزَلَ ·
فَرَّطَ/أَضَاعَ. Misleading: وَسْوَسَ/نَزَغَ/سَوَّلَ · أَضَلَّ/أَغْوَى · غَرَّ/خَدَعَ/خَادَعَ. People, wishes, money, water: مَلَأ/سَيِّد/كُبَرَاء ·
تَمَنَّى/أُمْنِيَّة/أَمَل · دَيْن/قَرْض · نَهَر/عَيْن/يَنْبُوع · عَذْب/فُرَات/مِلْح/أُجَاج. Verbs 500–601 landed on study-site only while the batch was finished, so members come
from the studied verbs and the noun catalogue. Drafted from the Mufradāt entries, verified (417 points: 384 confirmed, 30 partial,
2 different, 1 not found; 31 texts changed — verse numbers of wordings he quotes (23:33 not 7:60, 4:43 not 4:99, 2:218 not 8:74),
one of his two answers restored (23:14, Allah's iḍlāl), vowels he does not give left open (1:4)), reviewed blind (92 claims,
36 flagged, every flag fixed in the texts, none held back; 29 Bosnian quotes the reviewers found close to Korkut's sentences were
translated again). English quotes are Pickthall's words; where he gives two members one English word ("beguile", "deceive",
"led astray", "sent on before", "demon") the ayah is paraphrased or the member named in [brackets]. أَمَل and كُبَرَاء have no
Mufradāt entry of their own and rest on Quranic usage (all places read; كُبَرَاء is cited by him under أبا); thin members kept as
well-known pairs: مَلِيك, مُصَوِّر, طَرَحَ, طَلَبَ (1× each), أَسْلَفَ, أَكْمَه, عَذْب, مِلْح, يَنْبُوع (2×). Counts that include another sense are
noted per group: أَحَد with 'anyone', سَاعَة with 'hour', عَيْن with 'eye', جِنَّة with 'madness', مَالِك with the keeper of the Fire
(43:77). Left out on purpose: 18:110, 72:20, 79:42, 33:63, 80:2, 80:4, 6:68, 7:184, 7:200, 41:36, 3:196, 40:4, 73:10, 74:5, 38:69,
66:1, 33:51, 6:35 (said to or about the Prophet), 7:20, 20:120, 20:121 (Adam), 7:16, 15:39, 38:82, 18:50 (Iblīs), 11:34, 4:34,
23:67, 22:52, 12:24, 38:33, 5:6, 18:86, 2:223 (readings differ), 37:145 and 68:49 (his "of little account" is not put on Yunus),
39:53 (needs 4:48 beside it), 47:25 and 46:29 (named only), 33:50.

**The planned set is complete at 255 groups.** Good candidates for any future batch (not built): صَرَفَ/رَدَّ (drafted for batch 11
and set aside as the 26th), نُطْفَة/مَنِيّ, ظَهْر/صُلْب, بَطْن/جَوْف, حَيَاة/مَعِيشَة, اِقْتَدَى/أُسْوَة/إِمَام, عَزِيز/قَوِيّ/مَتِين, أَكْرَمَ/أَعَزَّ; pairs among
the verbs 500–601 (landed after this batch was drafted); particle groups (لَنْ/لَا, إِنْ/إِذَا) once fil.nuances.model has a particle identity.
Not buildable from the catalogue: Paradise names (فِرْدَوْس, عَدْن), شَيْطَان/إِبْلِيس, رِيح/رِيَاح (one lemma), حِجْر as intellect (1×).
