# Korijeni / Roots — the Quran's words by root (2026-11-06)

Arabic vocabulary is learned by root. A root page gathers every word the Quran derives from one root — its
verbs by form, its nouns, adjectives and participles — so a learner who knows قَالَ sees قَوْل, قَائِل, قِيل beside it.
Bosnian and English only, like nouns, adjectives, nuances and particles.

## What a root page shows
- The letters (ق و ل), what the root means — the meanings of its most frequent studied words, with their Arabic
  ("derived", never written by hand) — the corpus's count of the root (words of the Quran it stands in) and the
  number of its words.
- An optional core-idea line (below), only where it was verified.
- Every catalogued word of the root, grouped: verbs by form (I–X, with the pattern فَعَلَ … اِسْتَفْعَلَ; a four-letter
  root فَعْلَلَ, تَفَعْلَلَ, اِفْعَلَلَّ), nouns (with verbal nouns, adverbs and proper names, each labelled), adjectives,
  participles (active/passive, with the form they derive from). Each word: Arabic, kind, count, meaning, the card's
  checked clip, and a link to its card (verb, noun, adjective) or particle page where it has one.
- An unstudied word shows a meaning only where our data holds a vetted one — the verb, noun and adjective meaning
  files, or a near-synonym group member that stands for exactly one word; otherwise only its Arabic and its count.
- Links to the near-synonym groups holding any of its words, and "Vježbaj ovaj korijen": the exercise hub with
  `?w=verb:qala,noun:qawl&t=…` (site/exercises.js loads each asked word's shard and keeps the questions about any).
- The list (`/bs/korijen/`, `/en/root/`): alphabetical by the Arabic letters (every hamza under alif), a letter
  index, and a search box shown only with script that filters by letters, page name, the words bare of marks and
  their meanings. Verb, noun and adjective cards link their root letters to the root page (bs and en pages).

## Counts: every word of the root, once
A root's words come from our catalogues (fil.service verbs by root and form, fil.stages.nouns lemmas), so a root
page counts exactly what the cards count. The gate (`fil.roots.gate`) holds: the listed words add up to the corpus's
count of the root less the words our documented corrections (data/corpus_corrections.json, misattributions) read
as another word — the page says so where that happens (فطر: 20 in the corpus, 2 are تَفَطَّرَ read apart, 18 listed).
And every studied word (card or particle page) stands on its root's page, linked to all its pages. The gate runs in
the tests, in `fil roots check`, and stops `fil pages`.

## Page names
`q-w-l`, `ayn-l-m`, `a-m-n` (every hamza "a", ʿayn spelled out), decided once over all corpus roots, most frequent
first: roots that read alike (ح/ه, س/ص) give the less frequent `-2`. The corpus is fixed, so names never change.

## Core ideas (data/root_core_ideas.json)
One line per root, bs + en, our own words, grounded in ar-Rāġib's *Mufradāt* entry for the root and verified
against the OpenITI text (`0502RaghibIsbahani.Mufradat.JK001150-ara1`, CC BY-NC-SA 4.0, read locally in
build/openiti-mufradat/, never shipped or quoted; `fil nuances mufradat ROOT` prints the entries). No double
quotation marks (a core idea quotes no ayah), at most one line, a `verified` record of the headwords read as the
book spells them (كان for كون, شيء for شيأ, رب for ربب) and a note of what was confirmed — the model refuses
anything less. A root whose entry gives no base sense we can vouch for gets no line. The page label attributes
the line ("Našim riječima, prema natuknici … Mufradāt").

Batch 1 (60 roots, the most frequent with a studied word): drafted and verified entry by entry by three parallel
verifiers; 0 skipped. Reworded on merge: شيأ (the definitions are others' views in his entry: "some define it…
others tie it to willing"), "Allah" for "God", "Quran" spelling. Points a reviewer may revisit: كون ("came about"
is his reading for one ayah), قوم (the line keeps to standing; قَوْم "a people" left out), عذب (two senses, the link
disputed — said so), قلب ("it is said" kept as his hedge), حيي (six kinds of life listed, no single base).

## How it is built
- Engine, pure: `fil.roots.model` (words, pages, slugs, patterns, core ideas), `fil.roots.index` (the pages from
  `RootSources`), `fil.roots.gate`.
- Stage: `fil.stages.roots` (composition root: corpus, catalogues, corrections, meaning files, the cards `fil
  pages` built → pages; `fil roots check | show ROOT…`), `fil.stages.root_pages` (writes pages, sitemap paths, the
  app link), renderer `fil.pages.root_render`, interface text `rootPage` in site/ui.js, "Korijeni / Roots" in the top
  bar (`render._SECTIONS`) and the app.
- Tests: tests/test_roots.py — goldens (ق و ل grouping and 1722 = corpus; ع ل م by form; فطر corrected), the gate
  over the whole corpus, and the built site (every card's root link leads to a page that links it back).

## Next
More core ideas (next most frequent roots, same workflow); particles' roots beyond كَيْف/لَيْسَ/أَيْن/مَتَى/هُنَالِك as
their lemmas match the catalogues.
