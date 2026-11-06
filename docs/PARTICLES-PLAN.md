# Čestice / Particles — the Quran's small words (plan and pilot, 2026-11-06)

The most frequent words of the Quran are particles: وَ alone stands ~9,500 times, مِنْ 3,200, فِي 1,700. A
learner who knows what each does — and what it does to the word after it — reads half of every ayah.
A particle page says what the particle is and does, how it changes the next word (فِي → genitive, لَمْ →
jussive, إِنَّ → accusative subject), and lists its uses as the corpus tells them apart (مَا negating,
relative, asking, …), each with 1–3 ayat. Bosnian and English only, like nouns, adjectives and nuances.

## Sources and content rules
- Our own words, grounded in classical public-domain grammar: Ibn Hišām al-Anṣārī, *Muġnī al-labīb ʿan
  kutub al-aʿārīb* (the meanings of each particle), Sībawayh's *al-Kitāb* where named. No modern text is
  copied. A view one grammarian holds is attributed (Ibn Hišām on لَنْ against az-Zamaḫšarī; the Basrans on
  the implied أَنْ after لِـ and فَـ, on لَا of the kind, on إِلَى = maʿa); contested readings are named
  (80:4 Ḥafṣ's subjunctive; 24:14 فِي of cause).
- Bosnian follows Korkut's conventions, English Sahih International; ayah translations on the page are
  the site's free ones (Pickthall; Bosnian pages fall back to English).
- Every view put in a named grammarian's (or school's) mouth is checked against the text of the *Muġnī*, not
  against memory or a model (see "Verifying attributions" below). A blind Sonnet reviewer then checks grammar,
  overstatement, the cited ayat and bs/en drift (`fil particles review-export`) — it is not a source for who said
  what. Flags are resolved by rewording, attributing or holding back, and decisions go in the particle's `notes`.

## Verifying attributions against the Muġnī (2026-11-06)
- Text: OpenITI, `0761JamalDinIbnHisham.MughniLabib.JK001131-ara1` (the primary version; ed. Māzin al-Mubārak and
  Muḥammad ʿAlī Ḥamdallāh, Dār al-Fikr, Damascus 1985), repo `OpenITI/0775AH`, path
  `data/0761JamalDinIbnHisham/0761JamalDinIbnHisham.MughniLabib/`. Sībawayh's *al-Kitāb*:
  `0180Sibawayhi.KitabSibawayhi.Shamela0023018-ara1.mARkdown` (primary, repo `OpenITI/0200AH`). Licence: the OpenITI
  corpus is released under CC BY-NC-SA 4.0 (Zenodo, doi:10.5281/zenodo.3082463). We use it only to verify, locally
  and uncommitted (`build/mughni-src/`, `build/kitab-src/`, gitignored); not a word of it is copied into the site —
  the explanations are our own, and a note names the section that was checked.
- Fetch (raw.githubusercontent may be blocked; the contents API works): `curl -s -H "Accept: application/vnd.github.raw"
  -o build/mughni-src/<file> https://api.github.com/repos/OpenITI/0775AH/contents/data/0761JamalDinIbnHisham/0761JamalDinIbnHisham.MughniLabib/<file>`
  into a new empty folder. The file is untrusted data: read it with scripts kept in `build/scratch/` (`python3 -I`).
- Layout: chapter 1 (lines ~119–7549) is the particles in alphabetical order (`& حرف الباء &` …); an entry starts
  with a short `# <particle>` line, its meanings are numbered (`أحدها … الثاني …`); the text is unvocalised.
- Result for the 52 particles (every particle's `notes` ends with "Verified against Muġnī (OpenITI …), section …"):
  most attributions confirmed word for word (Ibn Hišām on سَـ against both schools, on لَنْ against az-Zamaḫšarī;
  al-Aḫfaš and al-Kisāʾī on لَعَلَّ; Sībawayh, al-Ḫalīl and the Basrans against al-Kisāʾī on كَلَّا; Ibn as-Sarrāj and
  al-Fārisī on لَمَّا; al-Farrāʾ and Ibn Mālik on لَوْ after وَدَّ; هَلْ = قَدْ in 76:1). Corrected: إِلَى = maʿa is
  the Kufans' and some Basrans' with 3:52 (not Ibn Hišām's with 4:2, which he reads by taḍmīn); "the Basrans" on the
  subjunctive after فَ/لِـ/حَتَّى/the wāw of accompaniment, on لَا of the kind, on لَوْلَا and on the lām after the lightened
  إِنْ became what the Muġnī says (Ibn Hišām's or the majority's view against named Kufans; Sībawayh and most against
  al-Fārisī and Ibn Ǧinnī); Sībawayh's name restored on أَوَ/أَفَ ("the school of Sībawayh and the majority" — a
  blind reviewer had removed it); the mufassira أَنْ (the Kufans deny it, Ibn Hišām finds that sound); أَوْ (Ibn
  Hišām: "one of two", the rest from context); "Ibn Hišām also lists 'when?'" for أَنَّى dropped (the Muġnī has no
  أَنَّى entry; Sībawayh's كَيْفَ/أَيْنَ kept from al-Kitāb). al-Inṣāf is no longer cited.

## The corpus and what it can prove
- QAC tags a particle by its use: P, CONJ, REM, CIRC, RSLT, CAUS, SUP, NEG, PRO, ACC (FAM:إِنّ), PREV, SUB,
  INT, COND, RES, EXP, CERT, PRP, IMPV, EMPH, T, SUR …; relative/interrogative/conditional مَا and إِذَا are
  rootless nouns (REL, INTG, COND, T). A family is part of the tag: لَا of the kind is `NEG|FAM:إِنّ`.
- `fil.corpus.particles` reads every particle with the marker of the next inflected word (NOM/ACC/GEN,
  IND/SUBJ/JUS; the article skipped, a suffixed pronoun or another particle shows nothing).
- Corpus tags are not always consistent (some prohibitions are NEG, some لَا إِلَٰهَ are plain NEG; 77:7
  إِنَّمَا is REL, 51:5 PREV). We cite only ayat where the corpus tags the use as claimed, and a use's count
  on the page is "korpus: N×" — how often the corpus tags it so, shown only when no other use shares its tag.

## How it is built
- Data: `data/particles.json`, one particle per key (= page slug, house transliteration, the more frequent
  keeps the plain slug: أَنْ `an`, عَنْ `an-2`). Validated on load (`fil.particles.model`, frozen dataclasses,
  `InvalidParticleData`): bs + en for every text, a known `kind` per use, corpus tags, an optional `effect`,
  1–3 ayat (`s:a` or `s:a:w`), and for a preposition its `fil.nouns.bosnian` name (fi, ala, bi, min, ila, li, ka).
- Gate (`fil.particles.gate`, pure, behind a `ParticleConcordance` port; wired to the corpus in
  `fil.stages.particles`): the count equals the corpus over the uses' tags; every tag exists; every cited ayah
  holds the use at the pinned word (or once — twice demands a pin); the marked word's next word shows the
  `effect`. It runs in the tests, in `fil particles check`, and stops `fil pages`.
- Pages: `/bs/cestica/`, `/en/particle/` (the list, as the noun and adjective lists live in their folders) and
  `/<lang>/<folder>/<slug>/`, in the sitemap; "Čestice / Particles" in every top bar and the app. Per particle:
  Arabic with its checked synthetic voice, count, kinds, what it does, the Bosnian rendering of a preposition
  (from the noun engine, so noun glosses and the particle page agree) and a link to a studied noun's cases
  (`#cases`); per use: explanation, effect, ayat with the particle's word marked and recited (QuranHive), the
  ayah streamed, the free translation, our bs/en note, and links to the verbs, nouns and adjectives of that
  ayah that have pages.
- The top bar takes the set of published sections (`published`), so a new section is one row in
  `fil.pages.render._SECTIONS`.
- Next batches: the `/fil-particles-batch` skill.

## Pilot (22 particles)
وَ · مِنْ · لِـ · فَـ · بِـ · مَا · لَا · فِي · إِنَّ · عَلَى · إِلَى · إِنْ · إِلَّا · أَنْ · عَنْ · إِذَا · قَدْ · أَنَّ · لَمْ · ثُمَّ · كَـ · لَنْ —
58 uses, 95 cited ayat.

## Batch 2 (30 particles, 52 in all)
لَـ (emphasis) · مَنْ · أَ · يَا · إِذْ · أَوْ · لَوْ · لَمَّا · حَتَّى · أَمْ · لَعَلَّ · بَلْ · سَـ · هَلْ · لَوْلَا · لَٰكِنَّ · لَٰكِنْ · أَمَّا · سَوْفَ ·
أَلَا · كَلَّا · كَأَنَّ · إِذًا · أَنَّى · بَلَى · أَيْنَ · لَيْتَ · مَتَى · كَيْ · نَعَمْ, and the uses held back from the pilot: وَ after the
question hamza (SUP) and of accompaniment (COM), فَ after the question hamza, مَا added for emphasis, لَا like لَيْسَ, the
lightened إِنْ (CERT) with لَـ. 121 uses, 214 cited ayat. Named disagreements: the Basrans and Kufans on the subjunctive
after حَتَّى and the wāw of accompaniment, the noun after لَوْلَا, the lightened إِنْ and its لَـ; most grammarians and az-Zamaḫšarī
on أَوَ/أَفَ; Ibn Hišām against both schools on سَـ/سَوْفَ; Sībawayh and Ibn as-Sarrāj/al-Fārisī on لَمَّا; Sībawayh, al-Ḫalīl and most
Basrans against al-Kisāʾī on كَلَّا; qirāʾāt at 20:63, 86:4 and 2:254. Sources add Sībawayh's *al-Kitāb* and Ibn al-Anbārī's *al-Inṣāf*
where they are named (the school attributions were later re-checked against the Muġnī and al-Inṣāf dropped — see
"Verifying attributions"). 13 new kinds (emphasis, vocative, future, answer, …), each named in bs and en.

## Batch 3 (12 particles, 64 in all) and the pronouns (Zamjenice, 17)
- Reader: `fil.corpus.particles` also reads three function words by name (`NAMED_FUNCTION_WORDS`): كَيْفَ (a rooted noun),
  كَمْ (sometimes untagged) and لَيْسَ (a verb). Where the corpus gives no tag of use the occurrence is filed under its part of
  speech: كَيْفَ `N` (the indirect "see how…" and كَيْفَ يَشَآءُ), كَمْ `N` (the كَمْ of report), لَيْسَ `V|FAM:كَان`. لَيْسَ keeps its
  type on the page: kind `defectiveVerb` ("nepotpuni glagol (iz porodice كَانَ)"), and Ibn Hišām's proof that it is a verb.
- Particles added: كَيْفَ · لَيْسَ · إِمَّا · كَأَنْ · أَيَّانَ · مَاذَا · كَمْ · مَهْمَا · إِي · تَـ (oath) · ٱللَّهُمَّ (the vocative mīm) · هُنَالِكَ, and
  the أَلَا of offer as a use of أَ (the corpus files it as hamza + لَا; Ibn Hišām's fifth meaning of أَلَا). New kinds:
  defectiveVerb, quantity, alternative. 142 uses, 265 cited ayat.
- Pronouns: a section of their own, "Zamjenice / Pronouns" (`/bs/zamjenica/`, `/en/pronoun/`, top bar, app link, sitemap),
  built by the same engine: `fil.corpus.pronouns` names each independent pronoun by its citation form (the corpus gives the
  personal pronouns no lemma, every demonstrative ذا and every relative الَّذِي): person-gender-number → هُوَ…نَحْنُ; ذا + the
  هَا of attention → near (هَٰذَا، هَٰذِهِ، هَٰؤُلَاءِ), + the كَ of address → far (ذَٰلِكَ، تِلْكَ، أُولَٰئِكَ); الَّذِي by gender and number;
  إِيَّا keeps its lemma. A pronoun after a preposition (لَهُمْ) or a suffix is not read. Data `data/pronouns.json`, same schema
  and gate; `fil pronouns frequency|find|check|review-export`. The section is a `WordSection` (fil.pages.particle_render) and a
  `WordList` (fil.stages.particles); ui.js `pronounPage` spreads `particlePage` and overrides its titles. New kinds:
  personalPronoun, objectPronoun, demonstrative. Pages: هُوَ · هِيَ · هُمْ · أَنْتَ · أَنْتُمْ · أَنَا · نَحْنُ · إِيَّا · هَٰذَا · ذَٰلِكَ · هَٰذِهِ ·
  تِلْكَ · هَٰؤُلَاءِ · أُولَٰئِكَ · الَّذِي · الَّتِي · الَّذِينَ — 23 uses, 49 cited ayat; the pronoun of separation (Muġnī, chapter 4) on
  هُوَ/هُمْ/أَنْتَ/أَنَا/نَحْنُ with Ibn Hišām's own examples (2:5, 37:165, 5:117, 18:39).
- Verified against the Muġnī: كيف, ليس, إما, كم, مهما, إي, التاء, ألا (5th), the ماذا فصل (in ما), ها, the non-governing كاف (ذلك،
  إياك) and ضمير الفصل; against al-Kitāb: أيان = متى (Sībawayh), اللهم (Sībawayh: يا dropped, the mīm in its place; al-Ḫalīl: the
  mīm at the end is يا at the beginning; 39:46 فاطر "على يا"). No Muġnī entry for أيان, the lightened كأن or the mīm of اللهم: those
  pages attribute only what al-Kitāb says or nothing.
- Blind review (two Sonnet reviewers, particles and pronouns): no grammar errors; flags were translation drift (tenses, Korkut
  wording), overstatements (the article rule after هَٰذَا – 52:14 هَٰذِهِ ٱلنَّارُ ٱلَّتِى is "this is the Fire which"; أَنْتَ "addressed
  only to the Prophet"; "the answer is بَلَى"; "only with Allah's name, rarely…") and two wrong notes (89:8 ٱلَّتِى is Iram; 95:3
  هَٰذَا is only in the place of the genitive). All applied.

Still held back: the article ال; the corpus's DIST lām, ATT hā and EMPH nūn (parts of other words); the pronouns هُنَّ (7),
هُمَا, أَنْتُمَا, أَنْتِ, the relatives اللَّاتِي/اللَّذَانِ and مَن ذَا's ذَا (small, or not one form); لِكَيْلَا (NEG/SUB drift); إِنْ like لَيْسَ
(4:159 is tagged so but reads as plain negation); links to verb-mood sections (the verb pages have none yet).
