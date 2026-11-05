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

## Spike findings (ffdfa3d0) and adjustments

- 3,125 lemmas catalogued (`fil nouns status|catalogue|paradigms`); 99.2% of 30,916 noun
  occurrences decompose cleanly; the governing preposition is captured (attached or the
  word before).
- QAC marks plurals only by gender+number; a broken plural carries its singular's lemma.
  945 lemmas have a plural: 377 sound masc., 117 sound fem., 519 broken; 88 have a dual.
- CAMeL (calima-msa-r13) declines nouns: for the top 600, 1,984 cells are Quranic, 2,172
  generated cells pass the gate (83% of what CAMeL produced), 1,232 stay empty.
- Adjustments: adverbs (بَيْن، عِنْد) get no case table · a second plural (كَافِرُون /
  كُفَّار) is its own row · empty cells stay empty, never forced · generated forms are
  shown in Quranic-style spelling or marked "standard spelling" · only ~70 of the top 600
  are picturable, so pictures also cover concrete nouns beyond the top 600 (fruit,
  animals, body, nature, objects), and the pilot's picturable 25 are hand-picked from
  `build/nouns/categories.tsv`.

## Pictures (owner decision: OpenMoji + Twemoji, recoloured)

- `data/noun_categories.json`: all 3,125 lemmas → category + picturable (Sonnet-classified,
  sacred/people/idol/body-of-a-person entries forced off by hand); 320 picturable.
- `data/noun_pictures.json`: per picturable noun its Bosnian name, slug (same as the future
  page slug), emoji codepoint and the reviewer's choice — openmoji 42, twemoji 159, none 119
  (112 with no fitting emoji, 7 rejected at review). Nouns with none get no picture.
- `fil nouns picture-candidates|pictures OPENMOJI_DIR TWEMOJI_DIR` rebuild candidates /
  `assets/nouns/<slug>.svg`; `tests/test_noun_pictures.py` gates every shipped file.
- Credit: `fil.pages.picture_credits.picture_credit` — wire into the footer of pages that
  show pictures when the noun pages exist.
