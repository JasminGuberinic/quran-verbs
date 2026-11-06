---
name: fil-surahs
description: Change the "Sure / Surahs" pages of the Fiʿl study site (a surah's vocabulary, coverage, first ayat, practice link), or explain a surah's coverage number. Use when the user says "/fil-surahs", "sure", "coverage of a surah", or asks why a word of a surah is (not) counted as taught.
---

# Surah pages (bs + en)

Goal and decisions: docs/SURAHS-PLAN.md. Rules as everywhere: bs + en only, never ask the owner (decide, write the
decision in the plan), commit and push to study-site (never main, never deploy).

- Engine (pure): src/fil/surahs/ — `headword` decides which part of a word is counted (verb > rooted noun >
  pronoun > stem particle > proclitic); `vocabulary` groups tokens into entries, computes coverage (rounded down)
  and holds the gate (every token in exactly one entry). Change the headword ranks only with a golden test.
- Coverage moves by itself: a new noun, verb, particle or pronoun card raises it at the next `fil pages`. Nothing is
  hand-counted; never write a coverage number into data or text.
- Meanings: only a card's vetted meaning, and a verb form's gloss from its card. An untaught word shows Arabic and a
  count, nothing more. Ayah translations: shipped Pickthall only (no Sahih, no Korkut).
- Names and Meccan/Medinan: data/surahs.json, copied from Tanzil's metadata (CC BY 3.0); credit stays on every page.
- Weight: keep al-Baqarah's page under the test's limit (rows lean, the ayat in ayat/sura-NNN.json).
- Links: a card only when its section is published; a root page only when `root_path` returns one (the Korijeni
  section). Arabic carries translate="no".
- Verify: `PYTHONPATH=src … -m pytest -q tests/test_surahs.py` (built tests need `fil pages` first), `node --test tests/js`.
