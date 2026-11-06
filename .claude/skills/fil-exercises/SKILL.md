---
name: fil-exercises
description: Add or change an exercise kind ("Vježbe / Exercises": picture → word, listen, verb form ↔ meaning, from the Quran, which case, preposition + case, adjective agreement, nuances, particles) on the Fiʿl study site, or refresh the exercises after a content batch. Use when the user says "/fil-exercises", "nova vježba", "add an exercise type", or asks why an exercise is wrong.
---

# Exercises (bs + en)

Goal: practice built only from content that already passed its gates (docs/EXERCISES-PLAN.md). Rules as everywhere:
bs + en only, never ask the owner linguistic questions (decide, write the decision in the plan), commit and push to
study-site (never main, never deploy). Engine: src/fil/exercises/ (pure: model, gate, text, shards, generators),
stage src/fil/stages/exercises.py (cards → generators → gate → shards), pages fil.stages.exercise_pages +
fil.pages.exercise_render, script src/fil/site/exercises.js, interface text site/ui.js `EXERCISE_PAGE`.

## Content rules (sacred)
- Never generate Arabic for an exercise. Every form shown is a checked table cell, a word of a reviewed sentence, or a
  word of the Quran from a card. Run-time JS only shuffles, shows and grades.
- Exactly one right answer — by a rule you can state, not by luck. A distractor must be wrong under every reading the
  corpus or our tables allow (a word read ACC or GEN: both readings), and never a form good Arabic also allows (plural
  adjectives beside a plural of things, 2:184; feminine singular beside a broken plural of people). When in doubt,
  leave the distractor out; when fewer than the minimum remain, skip the item.
- No tells: show Arabic options in one style (`text.in_one_style`), never mix Uthmani and standard spelling.
- Meaning options never share a content word in either language, never come from one root or one nuance group.
- A contested reading (a qirāʾa, a grammarians' dispute) is not a good question: prefer another ayah of the same use.
- Verb forms (src/fil/exercises/verb_forms.py): a spelling's readings are practice.js `readingsOf` (`text.reading_key` =
  `spellingKey`, a test runs both — change them together). Options of one verb's forms clash on the same gloss in
  either language (`text.same_gloss`), not on a shared word; each question passes its kind's `*_problems` validator
  (fail fast in the generator) before the gate. Meanings only where `compose_cell` composes them; never a you/she
  present in Iz Kur'ana, never active/passive twins, never a same-cell form differing by "and/so".
- Iz Kur'ana answers with the gloss of the place it shows: a place's own gloss (`Sources.place_glosses`, from
  data/composed_ayah_glosses.json — a polysemous verb's form in several senses, or a per-place correction) wins
  over the form's row. A gloss whose object is still "him/it"/"her/it" is never asked (`leaves_referent_open`):
  resolve the shown ayah in data/composed_place_corrections.json to bring it back.

## Working in an agent worktree
- Symlink `data/qac`, `data/quranhive`, `data/translations` to the main repo's; copy `build/nouns/*.tsv`; link
  `build/{speech,recitation,compressed}-cache`. Run `PYTHONPATH=src ~/Development/quran-verbs/.venv/bin/python -m
  fil.cli pages` (~10 min) and `… -m pytest -q`, `node --test tests/js`. Scratch scripts in `build/scratch/`
  (gitignored), written with the Write tool.
- Fast loop without a full build: dump the cards once (a scratch script wrapping `fil.stages.pages._write_site_files`
  to write the verbs/nouns/adjectives/nuances/particles cards to build/scratch/cards.json), then call
  `fil.stages.exercises.assemble(...)` with `read_sources()` (cache it with pickle) and print `counts()` and items.

## Adding a kind
1. Generator in src/fil/exercises/<family>.py: frozen input dataclasses in the generator's own terms (not card dicts),
   a pure function → `list[Exercise]`, the module docstring stating why the right answer is right and every distractor
   wrong. Reuse the engines' rules (agreement, sentence_gate.ROLE_CASES, particle effects) — never restate them.
2. Kind constant in `model.KINDS`; if its passage hides the word, add it to `gate._BLANKED`.
3. Adapter in fil.stages.exercises (`assemble`): card → inputs.
4. ui.js `EXERCISE_PAGE.<lang>.kinds.<kind>` {name, slug, intro, question} in bs and en, and any codes the options use;
   site/exercises.js `optionLabel` / `explanationLines` if it needs new wording.
5. Golden tests in tests/test_exercises.py (right answer, a distractor that must never appear, a case that must be
   skipped) and JS tests if the script changed. `fil pages` runs the gate over every real item.
6. Update the counts in docs/EXERCISES-PLAN.md.

## Verb forms (2026-11-06): form-meaning 1,249 · meaning-form 1,604 · quran-form 3,633
Lessons:
- `same_spelling` (nouns' `spelling_key`) is broad: it folds hamza seats and a silent final alif, so أَدْعُو ≈ اُدْعُوا. Fine
  for "never offer both", wrong for "is one spelling with two readings" — that is `is_read_alike`.
- English "you said" is 2MS and 2FS; Bosnian "kaže" is he and she, "rekli su" 3MP and 3MD: compare glosses per language.
- Quranic forms come with long ayat and translations: ≤ 30-word ayat, 20 forms a verb, and `shards` grows the count until no
  file is far over budget (a word's questions are never split).
- The Sources fields the verb kinds need (paradigms, polysemous, ayat, translations) default to empty: an old pickle in
  the fast loop gets them with `dataclasses.replace(sources, …)` from `read_sources()`.

## Pilot (2026-11-06): 7 kinds
picture 98 · listen 1,100 · case 2,382 · preposition 291 · agreement 303 · nuance 699 · particle 98.
Lessons:
- Picture pairs that look alike are many (قَلْب/فُؤَاد "srce", بَحْر/يَمّ "more", فُلْك/سَفِينَة, لِبَاس/ثِيَاب): exclude by
  meaning overlap in both languages, by emoji, by root and by nuance group — each catches cases the others miss.
- Table cells mix styles (attested Uthmani ٱلْأَرْضِ, CAMeL الرَّحِيمانِ): `in_one_style` before showing.
- A Quranic form after مِن carries the assimilation shadda of the word before (مِّن رَّبٍّ): compare with `standalone`.
- A noun before an adjective can have several readings (كَلِمَاتٍ is ACC or GEN): distractors must fail all of them.
- Shards keep each load < 70 KB; a word's shard is computed alike in Python and JS (golden test on both sides).
