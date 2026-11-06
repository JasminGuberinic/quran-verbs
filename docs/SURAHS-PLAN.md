# Sure / Surahs — the vocabulary of each surah (plan and first build, 2026-11-06)

Learners prepare a surah: Juz ʿAmma, Yā-Sīn, al-Mulk, al-Kahf. A surah page tells them how much of it they can
already read with what the site teaches (coverage), and lists every word it uses — the taught ones with their
meaning, card, recitation and first ayah, the others with their count — then its ayat with the free translation.
114 pages per language, Bosnian and English only, like nouns, adjectives, nuances and particles.
`/bs/sura/<n>-<slug>/`, `/en/surah/<n>-<slug>/` (`2-al-baqara`, `112-al-ikhlas`: the number first, so a page name
never changes), the list at `/bs/sura/`, `/en/surah/`; "Sure / Surahs" in every top bar and the app; indexed and in
the sitemap.

## What counts (decisions)
- **A token is a whole word** as the corpus numbers it (surah:ayah:word) — what a reader sees between two spaces.
  al-Ikhlāṣ has 15, al-Baqarah 6,116, the Quran 77,429.
- **Each token is counted once, under its headword** (`fil.surahs.headword`): the most lexical of its parts — a verb
  (or a function word the corpus files as a verb or rooted noun: لَيْسَ, كَيْفَ, كَمْ), else a rooted noun or
  adjective, else an independent pronoun / demonstrative / relative, else the particle that is the word's stem, else
  a proclitic particle. So وَلَمْ is لَمْ, لَهُ is لِـ (the ـهُ after a preposition is a suffix, not the pronoun هُوَ),
  فِيهِ is فِي, وَهُوَ is هُوَ, ذَٰلِكَ is the demonstrative. Proclitics and suffixes are not counted on their own:
  coverage would otherwise reward knowing وَ ten thousand times.
- **Covered** means the headword has a published card: a verb by "root_form" (where the corrected catalogue files
  the word, data/corpus_corrections.json — a passive is the same verb), a noun or adjective by "lemma|root", a particle
  or pronoun by the corpus tags its uses cover (مَا as a negation is the card's; مَا of a use no card describes is
  not). The percentage is rounded down: a page never claims more than it teaches.
- The Name (ٱللَّهُ), proper names and words with no card are listed untaught, with their count only: no meaning
  that has not been checked. A taught word shows its card's vetted meaning; a verb's forms show the gloss its page
  gives them (composed by rule, marked AI like everywhere).
- **Order**: by first appearance in the surah (a learner reading along); a switch (site/surah.js) reorders both lists
  by frequency in the surah. Without script the first order stays.
- **Recitation**: a taught word plays QuranHive's clip of where the Quran first says that very written word — the
  clip its card already ships — so 114 pages add few sound files. The first ayah streams like the verb pages'.
- **Meccan/Medinan** and the names are Tanzil's metadata (CC BY 3.0, data/surahs.json), credited on each page; the
  classification is shown as Tanzil's. The English name is shown on English pages only.
- **Ayat**: not in the page. `ayat/sura-NNN.json` (Arabic, the taught words marked where the surah first uses them)
  and `ayat/sura-NNN.en.json` (Pickthall, as shipped) load on request through site/ayat.js, 40 at a time. Bosnian
  pages show Pickthall with the site's "no free translation" note — no Korkut, no Sahih.
- **Weight**: a taught word is one row (its 3 commonest forms listed, the others counted; play icons drawn by CSS),
  the first 120 taught words open and the rest of a long surah folded in a `<details>` (the order switch sorts the
  parts as one list), an untaught word a chip inside a closed `<details>`. al-Baqarah, the heaviest: ~620 KB of
  HTML, ~65 KB as served compressed (a test holds < 800 KB / < 100 KB gzip). Pagination was weighed and left out: a
  learner sorting the whole surah by frequency needs it on one page.
- **Practice**: "Vježbaj riječi ove sure" opens the exercises hub with `?w=` naming the surah's most frequent words
  that have questions (at most 24, `exercise_render.MAX_SURAH_WORDS`, so a link loads a handful of shards) — the
  several-words practice the root pages brought — and `&s=surah`, so the hub says "only this surah's words".
- **Roots**: a verb, noun or adjective links its root's page (Korijeni) only when one is published
  (`surah_render.RootPath`, from `root_pages.slugs_by_root`: no page, no link).
- **Browser translation**: every Arabic element and the ayat list carry translate="no".

## The gate
`fil.surahs.vocabulary.problems`: every ayah of the surah from 1 to its last in order, every word of each from 1 on,
each token in exactly one entry, the entries' counts adding up to the surah's tokens. A failure stops `fil pages`.
The stage also holds the 114 surahs to the whole corpus (their tokens add up to it); a test holds that to 77,429,
and the built pages are checked row by row (the counts on each page add up to its surah's tokens).

## How it is built
- Domain (pure): `src/fil/surahs/` — `model` (Surah, Headword, Token, Taught), `headword`, `vocabulary` (entries,
  coverage, the gate). Data: `fil.surah_store` reads data/surahs.json and checks it against `fil.quran_numbering`.
- Stage (adapter): `fil.stages.surah_site` (corpus → tokens, the published cards → `SiteTeaching`, the views, the ayat
  files), `fil.stages.surah_pages` (writes them); wired in `fil.stages.pages.build`.
- Pages: `fil.pages.surah_render`; interface text site/ui.js `SURAH_PAGE`; script site/surah.js; styles pages.css.
- Tests: tests/test_surahs.py (al-Ikhlāṣ golden: 15 tokens, its headwords, 11 of 15 covered with the cards it has),
  tests/js/surah.test.mjs, the multi-word practice in tests/js/exercises.test.mjs.

## Next
- Bosnian surah names (Korkut's spelling, El-Bekara…) once a source we may use is chosen; Tanzil's transliteration
  until then.
- Juz grouping on the list (Juz ʿAmma first for beginners) if learners ask.
- A word-by-word gloss of the ayat list for the taught words.
