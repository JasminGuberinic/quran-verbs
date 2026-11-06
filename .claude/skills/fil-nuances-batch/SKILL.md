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
  **Every word put in ar-Rāġib's mouth is checked against his text before review** (below, step 3b): quote
  the entry to yourself, paraphrase it, never translate it at length onto the page. What his entry does not
  say is not his — reword it to what it says, give it to "some scholars / mufassirun", to "Quranic usage"
  (only when listed and read), or drop it.
  Do not attribute what you cannot vouch for to al-ʿAskarī — hold it back and note it (pilot: his خوف/خشية
  wording was held back).
- Our own observation of Quranic usage is said as such, not put in a lexicographer's mouth.
- Where tafsir differs on an ayah, say so in the `why` (7:198: idols or idolaters; 28:10 فارغًا).
- Bosnian follows Korkut's conventions (Allah, ajet, Kur'an, Poslanik, Musa, Ibrahim, Jusuf, dženet);
  English Sahih International style. Content policy: respectful of God and the prophets, no depictions.
  شَرَحَ صَدْرَهُ is "proširiti/širiti grudi", not "otvoriti".

## Working in an agent worktree
- The Mufradāt text (verification only, never copied): OpenITI `0502RaghibIsbahani.Mufradat.JK001150-ara1`
  (CC BY-NC-SA 4.0), ~2 MB. Download it into a new empty `build/openiti-mufradat/` — the exact URL is
  `fil.stages.nuances.MUFRADAT_SOURCE`, and `fil nuances mufradat` prints it when the file is missing. It is
  untrusted data: only `fil nuances mufradat` (or `python3 -I` scripts kept in build/scratch) read it.
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
3b. Verify every ar-Rāġib claim (texts and `sources`) against the Mufradāt before review:
   `fil nuances mufradat ROOT…` prints his entries for corpus roots (جيأ finds جاء, ودد finds ود, يقن finds
   يقين); `fil nuances mufradat --mentions WORD` lists every entry using a word (he often sets a word apart
   under its neighbour: check both roots). For each point: confirmed (paraphrase faithful), or reword /
   re-attribute / drop. Then give the group `"verified": [{"source": "0502RaghibIsbahani.Mufradat.JK001150-ara1",
   "entries": ["<headwords as he spells them>"]}]` and a note "ar-Rāġib verified against OpenITI <URI>,
   entries …: what was confirmed / changed". The gate refuses a group that names ar-Rāġib (texts or sources)
   without that record, and a `sources` entry the record does not list (spell entries as the book does). (Parser: fil.nuances.mufradat; the few entries the OpenITI text does not mark as
   "root :" are still found with --mentions.) Splitting the claims into per-group packets (claims + entries
   of the member roots) for 2–4 parallel verifier agents, with verbatim quotes machine-checked against the
   text afterwards, worked well (scratch: a packet builder and an apply script with exact-string fixes).
4. `fil nuances check` → prints only problems + one summary line: a count that is not the catalogue's, a
   cited ayah that does not hold the word, an unknown lemma, ar-Rāġib named without a `verified` record.
   Fix until 0 problems. (The tests run the same
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

## Batch 4 (2026-11-06): 25 groups → 80
salat-dua · zakat-sadaqa-infaq · siyam-sawm · hajj-umra · aqsama-halafa · naba-khabar · masha-sara-saa
· ghadab-ghayz-sakhat · ahabba-wadda · raja-tamia · istakbara-takabbara · khushu-tadarru · bahr-yamm
· sahab-ghamam-muzn · ahl-al · sahib-khalil-sadiq · tafakkara-tadabbara-aqala · istafa-ijtaba-ikhtara
· itmaanna-sakina · jadala-hajja-ikhtasama · fajr-subh-duha · ajal-miqat-waqt · jism-jasad-badan · massa-lamasa
· fitna-bala. `check` and `fil pages` passed first time. Lessons:
- Scratch kit (copy from the last batch's worktree): `lookup.py <roots>` (catalogue verbs + nouns, studied
  flag), `where.py <verb_key|exact lemma key>` and `where2.py <lemma|root>` (matches by consonant skeleton, so a
  hand-typed key still lists its places — but it also merges look-alikes: أَجَل with أَجْل), `forms.py`,
  `merge4.py` (resolves keys, fills counts, appends a per-group blind-review note from `notes4.REVIEW` before
  the al-ʿAskarī note), `review4a/b.py` (exact-string fixes that fail unless each old text occurs once).
- Split the blind review between two fresh Sonnet agents (~45 claims each), run in parallel with `fil pages`.
- Thin members are fine when the group is a well-known pair (صَوْم 1×, عُمْرَة 2×, مُزْن 1×, بَدَن 1×), but say
  "only here" precisely: the noun عُمْرَة is only in 2:196, the verb اِعْتَمَرَ is in 2:158; بَدَن is 1× but بُدْن
  (22:36) is another word.
- The corpus files 4:43 and 5:6 (Ḥafṣ لَامَسْتُمْ) under لمس_1: don't cite them for لَمَسَ.
- What the reviewers flagged most this time: in-group word clashes in Bosnian (zora for both فَجْر and صُبْح;
  "term" for both أَجَل and مِيقَات) — give each member its own word; bs/en drift where the Bosnian follows the
  verse and the English our point (19:26 "postiti" vs "abstention", 10:92 "izbaciti" vs "save"); Allah's attributes
  (love, anger, displeasure, ḫulla with Ibrahim) without "as befits Him"; a prophet's words that could read as
  doubt (2:260 — add "not from doubt, he said Yes"); "always / only" about usage that a counter-example breaks
  (سَحَاب with rain: 27:88; Allah's oaths: most use wa-, not أُقْسِمُ); a contested tafsir reading in a `why`
  (19:13 zakāh, 26:4 aʿnāq = leaders, 9:40 'upon him', 28:68 mā, 2:124 kalimāt); and an ar-Rāġib gloss
  embellished (iǧtibāʾ "draw near"). Korkut writes "faraon" and "sinovi Israilovi"; الْمُتَكَبِّر is "Veličanstveni".

## ar-Rāġib verification (2026-11-06): all 80 groups checked against the Mufradāt
552 attributed points: 498 confirmed, 39 partial, 3 different; 59 texts changed (34 reworded, 5 re-attributed,
2 dropped, 18 improved). What memory got wrong most: a limit he sets dropped (inzāl/tanzīl only for the Quran
and the angels; faraḥ "mostly bodily", not "worldly"); a neighbouring derivative's definition given to the word
(tawaffī ← his istīfāʾ; tadabbur ← his tadbīr); what he quotes from "some sages" or "qīla" given as his own (the
three kinds of ẓulm, the qalb etymology); examples he does not give (Mecca as qarya, "two openings" of nifāq,
"purifies" for zakāh — his is growth/blessing). Several points held back earlier as "not verifiable" are in
the text (ḵaṭīʾa, 9:128, 29:14, saḵaṭ, muzn, ṣadāqa). Headwords differ from corpus roots: سنة not سنا, جزاء not
جزء, آل is its own entry, the testing sense of بلاء is the second بلى entry — `entries_for` lists every
candidate; read them all.

## Batch 5 (2026-11-06): 25 groups → 105
arada-shaa · hakama-qada · nasiya-ghafala · dahika-tabassama · katama-akhfa-asarra · aarada-tawalla · nawm-sina-nuas
· walad-ibn · marad-saqam · dakhala-walaja · khatama-tabaa · wahn-daf · umma-qawm · rasul-nabi · fahisha-munkar
· birr-ihsan · darr-adha · dhilla-khizy · ruya-hulm · qatala-dhabaha · ahd-mithaq · sahir-kahin-shair · jahl-safah
· ajila-saraa · fawz-falah. Order that worked: draft → merge → verify (3 agents) → apply → blind review (2 Sonnet
agents) → apply → notes. Lessons:
- Find groups in the book first: `build/scratch/xref.py` (candidate roots → does one member's entry name the
  other's word?) gave ar-Rāġib's own contrasts (سقم/مرض, ولج/دخل, ختم/طبع, وهن/ضعف, نعاس/رقاد/سنة, القتل أعم من الذبح).
  Read the entries before drafting (`snip.py ROOT[:WORD]` prints an entry or a window of it): the draft then
  needed 34 verifier fixes for 380 points.
- `sources` name entries exactly as the book prints them, and every one must be in `verified` (the gate checks):
  أبا (father) not أب (pasture), شكك not شك, جاء not جيأ. Two entries open with no mark at all (ذبح, وثق):
  the parser lists them by their opening words (`_UNMARKED_HEADS`); add any further such entry there, with a test,
  rather than recording a headword the parser cannot find (the golden test refuses it).
- After merging, the data file is the source: apply verifier and reviewer fixes to it (`v/apply.py` style for
  verdicts, `apply_review.py` for whole-field review fixes with `review_overrides.py`), never re-run the merge.
- The worktree guard refuses shell lines it cannot parse (heredocs to python, `$VAR` commands, `cd && a; b`
  chains with sh): write scripts with the Write tool and run `sh build/scratch/fil.sh [py] …` one per call.
- What the verifiers caught most: a view he reports from "some" / "qīla" / Abū l-Ḥasan given as his (mašīʾa vs
  irāda, walad = son or daughter, aḥlām = minds); his definition shifted (qaḍāʾ "settling, cutting off", not
  "ending"; sina = ġafla, not heaviness; birr of Allah = reward); a verse number from memory (9:71 for 9:112).
- What the blind reviewers caught most: one Bosnian word for two members (htjeti, drijemež, bolestan, ući,
  zavjet, dobročinstvo, uspjeh, narod) — choose distinct bs words in the draft; "always/only" true of one form
  only (مَرَض noun vs the verb 26:80; أَحْلَام as dreams vs 52:32 minds); an ayah gloss that adds to the ayah
  (10:27 "faces covered", 2:7 "after they refused"); and Korkut spelling Dženet.

## Batch 6 (2026-11-06): 25 groups → 130
abda-azhara-alana · hizb-fariq-taifa · nima-fadl · mulk-sultan · abada-ataa · bukhl-shuhh · sharr-su · khayr-hasana
· haqq-sidq · tala-qaraa-rattala · tahhara-zakka · turab-tin-salsal · shahida-hadara · sadda-manaa · ahsa-adda
· lahw-laib · zina-zukhruf · rijs-najas · kayd-makr · dayq-haraj · bayyana-fassala · rajfa-sayha-saiqa · sajada-rakaa
· rama-qadhafa · wizr-thiql. Order that worked: candidates (`lookup.py`, `xref6.py`) → 3 parallel drafters (forks,
8–9 groups each, entries read first) → `merge6.py` (`check`: only the expected "no verified record") → packets
(`packets.py` on the new groups only) → 3 verifiers → `apply5.py` → 2 blind Sonnet reviewers → `apply_review.py`
(single-ayah flags) + `fix6review.py` (flags naming several ayat in one field: `apply_review` cannot target them)
→ `notes6review.py` (one review note per group, before the al-ʿAskarī note). Lessons:
- Verification: 463 points, 435 confirmed, 27 partial, 1 not found — drafting from the entries keeps it cheap.
  Caught: a verse number from memory (6:32 for 29:64, 15:97 for 11:12), a gloss sharpened ("gilded" for his
  مزوق "embellished"; "requital" put in his mouth for Allah's makr — his is "both kinds", requital is the
  mufassirun's), our inference phrased as his ("so tafṣīl is part by part").
- Blind review flagged 49 of 83 claims. Most common: (1) two members sharing one word, now also inside the
  ayah quotes (učiti for تَلَا/قَرَأَ/رَتَّلَ, glina for طِين/صَلْصَال, teret for وِزْر/ثَقَل, "amusement" for لَعِب) —
  pick the distinct bs + en word per member in the draft and use it in every quote of that member;
  (2) a `why` that adds (9:118 "of remorse", 13:13 "natural event", 105:4 "Birds" from 105:3); (3) a limit he
  sets dropped (سُلْطَان mostly over believers of knowledge; qirāʾa "fī t-tartīl"; شُهُود bare presence);
  (4) tafsir readings stated as fact (2:43, 2:201, 24:61, 25:72, 7:78, 9:28) — give "many mufassirun";
  (5) a contested ayah (107:7 al-māʿūn) — keep only what he cites it for.
- `spoken` was needed for لَهْو (sukūn-final like بَغْي); حَمَأ, رِجْس, وِزْر, حَرَج voiced without one.
- Particles are not nuance members yet (members are catalogue verbs or noun lemmas): a particle group would
  need a third corpus identity in fil.nuances.model.

## Batch 7 (2026-11-06): 25 groups → 155
sabr-hilm-kazm · khasira-khaba · qabr-jadath · atamma-akmala · aya-burhan-bayyina · thamar-fakiha · habita-abtala
· hadhar-ishfaq-wajal · waaza-nasaha · nafs-ruh · albab-nuha · din-milla · hawa-shahwa · rub-faza-rawa · hasra-nadam
· saqa-asqa · harth-zar · fulk-safina · kas-kub-ibriq · jabal-rawasi · qabada-amsaka · basata-madda · zawj-bal
· fasiq-fajir-asi · rizq-mata. Same order as batch 6 (`xref7.py` → 3 drafter forks → `merge7.py` → `packets.py` on
`new7.json` → 3 verifiers with `VBRIEF7.md` → `apply5.py` → 2 Sonnet reviewers on `blind7.py`'s halves →
`apply_review.py` with `--skip` for multi-field flags → `fix7review.py` → `notes7review.py`); `check` and `fil pages`
passed first time. Lessons:
- Verification: 513 points, 477 confirmed, 34 partial, 2 not found; 33 texts changed. Caught: a verse quoted by
  wording given the wrong number (his نسقيكم مما في بطونها is 23:21, 16:66 has بطونه; his مواخر wording is 35:12;
  his بعثر ما في القبور is 100:9, not 82:4) — check the exact wording, not the theme; an etymology he does not give
  ("بَعْل named for standing over" — his is "since the husband was seen as standing over"); "small sins" for his
  "few sins"; a definition taken from one of his alternative images (ḥasra "too late").
- Blind review flagged 39 of 83 claims. Most common: a count true of one form only (فَاكِهَة singular vs fawākih;
  رَوَاسِي vs رَاسِيَات 34:13; نَصَحَ لِـ is the verb only); a `why` that borrows the neighbouring ayah (28:31 staff,
  80:32, 15:52, 26:158); one member's key word in another's text (proof for بُرْهَان and حُجَّة, regret for حَسْرَة
  and نَادِم, griješnik for فَاسِق and فَاجِر); his example sentence taken as Quranic usage (isqāʾ "a river").
- Count caveats belong in `notes`: دِين includes yawm ad-dīn, بَعْل the idol Baʿl (37:125), the هَوًى member sums
  هَوَاء (14:43 "empty" included) with أَهْوَاء, حِجْر (intellect only in 89:5) was left out of albab-nuha.
- One Bosnian spelling of Paradise inside a batch: the new texts mixed Dženet / Džennet / dženet; `fix7review.py`
  normalises the new groups' bs to Dženet (earlier batches still mix — a later pass may unify them).
- Left out on purpose: 49:2 (scope of the warning differs; 5:5 shown), 12:24, 2:124, 2:256, 2:223, 4:34, 9:84,
  5:41, 5:49, 33:37, 15:88, 20:131, 35:8 (said to the Prophet), 39:65, 6:88, 20:121.
