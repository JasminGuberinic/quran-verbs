# Vježbe / Exercises — practice built from what has passed the gates (plan and pilot, 2026-11-06)

The cards teach; the exercises ask. Every question is built at build time from content that already passed its own
gate — a noun's checked case table, a reviewed practice sentence, an ayah the corpus places a word in — and written as
compact JSON; the page only shows, shuffles and grades. No Arabic is ever made up at run time or for an exercise.
Bosnian and English only, like nouns, adjectives, nuances and particles.

## Rules (sacred)
- **Exactly one right answer.** The build-time gate (`fil.exercises.gate`) refuses an exercise with zero or two right
  options, two Arabic options that are one word as a reader sees it (`spelling_key`: ٱلْأَرْضِ = الْأَرْضِ), two meaning
  options sharing a content word in either language ("srce" / "srce, duša"), a code offered twice, a blanked passage
  without its blank, a text missing a language, or a key used twice. A problem stops `fil pages`.
- **Distractors plausible but provably wrong**, by each generator's own rule (below). Where good Arabic allows a second
  form, it is never offered as wrong (a plural adjective beside a plural of things: أَيَّامًا مَعْدُودَاتٍ, 2:184).
- **One style.** Arabic options are shown in one spelling (`text.in_one_style`: standard alif for the Uthmani wasla,
  the vowel of a doubled letter and before a long ā written) so the Quran's own spelling of the right one gives nothing
  away; the Quranic form itself is shown after answering, with its recitation.
- Content policy as everywhere; the explanations shown after answering are the cards' reviewed texts (a nuance's "why",
  a particle use's note) or fixed interface sentences (site/ui.js `EXERCISE_PAGE`) filled with checked facts.

## The kinds (pilot: 7, then the verb forms: 10)
| kind | from | right answer | distractors |
|---|---|---|---|
| Slika → riječ / Picture → word | noun cards with a picture | the noun's lemma | other pictured nouns, same category first; never the same root, the same emoji, an overlapping meaning, or a member of the same nuance group (قَلْب/فُؤَاد/صَدْر) |
| Čuj i izaberi / Listen and choose | noun and verb cards' checked voice | the word's meaning | meanings of words of the same family and about the same frequency, under the same exclusions |
| Oblik → značenje / Form → meaning | the verbs' checked tables (the cells Arabic uses), with the checked voice | the cell's meaning composed by the rules that gloss the Quran's forms (`compose_cell`: English from the verb's first sense, Bosnian from its paradigm); a spelling with two readings (تَقُولُ, قُلْنَ) is asked once, with both as its one answer ("kažeš / kaže") | meanings of other cells of the same verb (the same person in another tense first, then the same tense); never a reading of the shown spelling, never two meanings that are one in Bosnian or in English ("you said": قُلْتَ / قُلْتِ) |
| Značenje → oblik / Meaning → form | the same composed meanings | the cell's form, heard after answering | two other cells of the same verb and the same cell of another verb of the same pattern (fair by `vocabulary.is_fair_distractor`: not the same root, not a near-synonym, no shared content word); never a form any reading of whose spelling has the asked meaning in either language |
| Iz Kur'ana / From the Quran | the "U Kur'anu" forms with one reading and a bs+en gloss, in the card's example ayah glossed alike, else their first ayah (≤ 30 words); 20 commonest forms a verb | the form's gloss | glosses of other forms of the same verb with another cell (tense, person, voice or object) — never the same cell with another "and/so", never the other voice (قَتَلَ/قُتِلَ), never a cell the table spells alike, never the same gloss. A present that may be "you" or "she" (تَقُولُ, تَقُولَانِ) is not asked; a gloss opening with an enclitic ("smo je prostrli") is neither asked nor offered. After answering: the word recited (QuranHive), the translation, quran.com |
| Koji padež? / Which case? | the nouns' reviewed practice sentences (4 roles each) | the role the sentence was written and gated for: subject NOM, object ACC, after a preposition GEN, possessor in an iḍāfa GEN | the three other (case, reason) pairs; after answering, the word's Bosnian rendering in that sentence |
| Prijedlog i padež / Preposition and case | the noun cards' Quranic forms after a separate preposition (فِي، عَلَى، مِنْ، إِلَى، عَنْ), nothing attached, glossed | the noun's genitive table cell of that number and definiteness, which must be the Quran's form | the nominative and accusative cells; skipped when one is spelled like the genitive (sound plurals, diptotes). After answering: the Quranic form recited, the ayah, the Bosnian rendering with its Bosnian case (fil.nouns.bosnian) |
| Slaganje pridjeva / Adjective agreement | the adjectives' reviewed attribute sentences | the form the sentence says | other cells of the adjective that agree with no reading of the noun by `fil.adjectives.agreement`, and are not a form good Arabic also allows (any plural beside a plural of things; the feminine singular beside a broken plural of people); one difference each where possible (gender/number, case, definiteness) |
| Nijanse / Nuances | the nuance groups' cited ayat, the member's word blanked | the member the ayah is cited for | the group's other members (it is a question of fact: what the Quran says there); an ayah cited for two members is never asked. After answering: the word recited and the group's "why" |
| Čestica / Particle | the particle uses with an effect, in their cited ayat (the particle marked) | the use's effect, which the particle gate holds to the corpus's reading of the next word | the other two cases (before a noun) or moods (before a verb) |

**Verb forms** (2026-11-06) are the app's "Oblik" and "Značenje" practice (practice.js) moved to the static pages, built
at build time under the same fairness rules rather than copied: a spelling's readings are `practice.js readingsOf`,
and `text.reading_key` is its `spellingKey` word for word (a test runs both). Each question also passes the
exactly-one-right-answer validator of its kind (`verb_forms.*_problems`; a problem stops the build), and the gate holds
meaning options of one verb to "never the same meaning in either language" instead of "no shared content word" (the
forms of one verb share it: "rekao je" / "rekli su"). Verb pages get "Vježbaj ovaj glagol / Practise this verb".

Decisions: only meanings that are composed by rule (a cell without Bosnian in its paradigm, a polysemous or idiomatic
verb, is not asked); Iz Kur'ana takes the gloss the verb's page shows (in context, or composed) and only forms with one
reading — the gloss of the very place it shows where that place has its own (a polysemous verb's form in several
senses, a referent resolved per place), and never a gloss whose object is still "him/it"/"her/it"; options are fully voweled, so forms one skeleton apart in the table (قُلْتُ / قُلْتَ) are fair — the meaning
names person and tense; active/passive twins are never offered against each other in Iz Kur'ana (the tables have no
passive cells). Shards grow until no file is far over budget (a heavy word gets fewer neighbours).

## How it is built
- Domain (pure): `src/fil/exercises/` — `model` (Exercise, Option, Segment, frozen), `gate`, `text` (spelling,
  meaning overlap, one style, stable order), the generators `vocabulary`, `cases`, `prepositions`, `agreement`, `ayat`, `verb_forms`,
  and `shards`.
- Stage (adapter): `fil.stages.exercises` reads the cards `fil pages` has built (plus the pictures' emoji, the noun
  categories, the studied nouns' readings `fil.stages.adjectives.noun_readings`, the Bosnian nouns), runs the generators
  and the gate, and writes `exercises/<kind>-<n>.json`.
- Size: each kind is split into shards of ~60 KB by its word (`shard_of`: FNV-1a of the word id, computed alike in
  Python and site/exercises.js), so a page loads one shard: a random one for a kind, the word's own one for "Vježbaj".
- Pages (`fil.stages.exercise_pages`, `fil.pages.exercise_render`): `/bs/vjezbe/`, `/en/exercises/` (hub: every kind
  with its count, and a mixed practice) and a page per kind (`/bs/vjezbe/koji-padez/`, `/en/exercises/which-case/`, …),
  indexed and in the sitemap; "Vježbe / Exercises" in every top bar (`render._SECTIONS`) and the app. Noun, adjective,
  nuance and particle pages get "Vježbaj ovu riječ / Practise this word" → `vjezbe/?w=noun:ard&t=picture,case,…`; verb pages "Vježbaj ovaj glagol / Practise this verb" (bs and en pages only).
- Page script `site/exercises.js`: pure core under `node --test` (tests/js/exercises.test.mjs) + DOM wiring. Sessions
  of 10; due questions first, then new ones; a missed question comes back 3 questions later in the same session and is
  due at once next time; Leitner boxes 0/1/3/7/21 days. Progress, score and streak in localStorage only, every access in
  try/catch. Keyboard: options are buttons, keys 1–4 choose, focus moves to the question and then to "Next"; feedback
  in an aria-live region; Arabic is `lang="ar" dir="rtl"`; one column of options on a phone. Sounds play through
  player.js (`data-audio`), so every play button is also a stop button.

## Pilot counts (2026-11-06)
picture 98 · listen 1,100 (600 nouns + 500 verbs) · case 2,382 · preposition 291 · agreement 303 · nuance 699 (105 groups) ·
particle 98. Ayat whose note names another reading are left out (80:4, 2:254 for particles).

Verb forms (600 verbs studied): form-meaning 1,254 (192 verbs) · meaning-form 1,643 (284 verbs) · quran-form 3,680 (391 verbs; polysemous verbs asked place by place). Fewer verbs
than 600 because a cell is asked only with a composed meaning (the Bosnian paradigms hold the cells the Quran uses).

## Next
- Verb forms: more Bosnian paradigm cells (fil compose sheets) → more verbs asked; the app's "Ajet" and "Rečenica" kinds.
- Particles' "which particle fits" (needs a rule that no other particle fits the slot — hold back until it can be gated).
- More sentences → more agreement and case items; translate the exercise interface with the rest of the site (step 4).
