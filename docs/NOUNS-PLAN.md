# Phase 3 — Quranic nouns and adjectives (plan, 2026-11-05)

Goal: learn every noun and adjective of the Quran, and how it is *used*: as subject,
object, after a preposition, in possession — "jede jabuku", "sjedi na drvetu",
"udario je štapom", "knjiga dječaka". Bosnian first, English second; other languages
later (same rule as all new features: en + bs only for now).

## What the Quran has (QAC corpus, words with a root)

| | lemmas | occurrences | top 100 | top 300 | top 600 | top 1000 |
|---|---|---|---|---|---|---|
| nouns (incl. participles, verbal nouns) | 2,934 | 25,870 | 51% | 72% | 83% | 89% |
| adjectives | 428 | 1,956 | 79% | 93% | 100% | |
| proper names | 44 | 3,090 | | | | |

Participles (مُؤْمِن, كَافِر — 2,713 occurrences) are taught as nouns/adjectives and
linked to their verb page. Proper names (prophets, places) get a simple list, no images.

## The noun card

1. **Header:** lemma with harakat, picture (concrete nouns only), meaning bs/en, root
   (link to the verb page when the root has one of our 500 verbs), gender, category.
2. **Number:** singular / dual / plural — sound and *broken* plurals as the Quran uses them
   (from the corpus; generated with CAMeL and gated where the Quran lacks one).
3. **Cases — the heart of it.** A table definite × indefinite × NOM/ACC/GEN with audio,
   and for each case *what it does*, with the Bosnian case it maps to:
   - NOM (-u): subject — الْوَلَدُ يَأْكُلُ "dječak jede" (nominativ)
   - ACC (-a): object — يَأْكُلُ التُّفَّاحَةَ "jede jabuku" (akuzativ)
   - GEN (-i) after a preposition — the preposition chooses the Bosnian case:
     فِي/عَلَى → lokativ ("u kući", "na drvetu"), بِـ → instrumental ("štapom"),
     مِنْ → genitiv ("iz kuće"), إِلَى → "do/prema", لِـ → dativ/"za"
   - GEN in possession (iḍāfa): كِتَابُ الْوَلَدِ "knjiga dječaka"; and possessive
     suffixes: كِتَابُهُ "njegova knjiga", كِتَابُنَا "naša knjiga".
4. **Practice sentences** (verbs we already teach + this noun): one per role — subject,
   object, after a preposition, possession. Same gate + blind review + content policy.
5. **U Kur'anu:** every Quranic form of the noun (بِأَيْدِيهِمْ, وَالْأَرْضِ, فِي الْأَرْضِ…),
   count, click-to-hear (QuranHive), composed en+bs gloss, example ayat, all ayat — the
   verb machinery reused.

**Adjectives:** the same plus agreement: الْبَيْتُ الْكَبِيرُ / بَيْتٌ كَبِيرٌ / الشَّجَرَةُ
الْكَبِيرَةُ — gender, number, case and definiteness follow the noun; non-human plurals
take feminine singular.

## Categories and pictures

- Every lemma gets one category from a fixed list: voće i povrće · hrana i piće ·
  životinje · dijelovi tijela · priroda i nebo · voda i more · kuća i predmeti ·
  odjeća · ljudi i porodica · vrijeme · mjesta · brojevi i količine · vjera i ahiret ·
  osobine i osjećanja · apstraktno. Browse by category in the app.
- **Pictures only for concrete things** (fruit, animals, body parts, nature, objects).
  Content policy: no people's faces, no prophets, angels or anything sacred depicted.
- **Style:** flat, 2–3 tones of the site's green, one object, recognisable at 64 px.
  Cheapest options, to be compared on a sample page before choosing:
  (a) open-licence icon sets (OpenMoji, Twemoji, Noto Emoji…) recoloured by a script
  to our palette — free, instant, recognisable; licence checked per set;
  (b) small SVGs drawn by a model in our palette — for what the sets lack.
  Images are tiny SVGs, bundled, one per lemma.

## How it is built (same tooling style as the verbs)

- **Engine:** noun catalogue from the corpus (lemma, root, gender, number, plurals,
  forms with clitics, frequency) · CAMeL generation for missing case/number forms,
  checked by the gate · composition of form glosses (proclitic + preposition → Bosnian
  case + noun cell + possessive), reusing the verb composer.
- **Bosnian declension:** per noun a paradigm written once (7 cases × sg/pl, only the
  cells the composer needs) by Sonnet sub-agents, validated on import — like the verb
  paradigms. English is rule-based (article, "of", "his", plural).
- **Commands:** `fil nouns plan | catalogue | categories | images | paradigms | forms |
  draft | check | review-export | review-import`, plus a `/fil-nouns-batch` skill.
- **Pages:** `/bs/imenica/<slug>/`, `/en/noun/<slug>/` (+ adjectives), SEO like the verbs,
  only bs/en built for now; app gets an "Imenice" tab with categories.
- **Exercises:** picture → word, "koji padež?", complete the ending, match the adjective
  to the noun, put the noun in the right case after a preposition.

## Order of work

1. **Spike (now):** noun catalogue + case/plural generation + form decomposition on the
   data; image-style comparison page for the owner to choose.
2. **Pilot batch of 50:** the 25 most frequent nouns + 25 concrete, picturable ones
   (jabuka, drvo, ruka, voda, kamila…) end to end: card, pictures, cases, sentences,
   forms, pages. Owner reviews.
3. Exercises and the "Imenice" tab with categories.
4. Adjectives.
5. Batches of 50 by frequency to ~600 nouns (83% of noun occurrences) + all adjectives,
   one batch per new session, then the rest.
