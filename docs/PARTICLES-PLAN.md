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
- A blind Sonnet reviewer checks every claim (`fil particles review-export`); flags are resolved by
  rewording, attributing or holding back, and decisions go in the particle's `notes`.

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
where they are named. 13 new kinds (emphasis, vocative, future, answer, …), each named in bs and en.

Still held back: the article ال; the corpus's DIST lām, ATT hā (هَٰذَا) and EMPH nūn (parts of other words); كَيْفَ,
لَيْسَ, إِيَّا (the reader takes only rootless function nouns and particles); إِمَّا, كَأَنْ, أَيَّانَ, مَاذَا, كَمْ, مَهْمَا, إِي; links
to verb-mood sections (the verb pages have none yet).
