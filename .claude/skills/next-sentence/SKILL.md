---
name: next-sentence
description: Draft the next practice sentence the factory owes, using the agenda and the brief. Use when adding practice sentences to verbs in the Fiʿl content engine, or when the user says "next sentence", "keep drafting", or asks to work through the agenda.
---

# Draft the next sentence the factory owes

One job at a time, and every fact comes from a tool rather than from memory. You compose;
the engine decides whether what you composed is acceptable.

## The loop

1. **`next_sentence_job()`** — one call gives you the job and its brief: the verb, the cell
   to demonstrate, the form to use, the cells already covered, and candidate words from the
   Quranic bank with the lexicon's own English glosses.

2. **Write the sentence from the brief.**
   - Use `writable_form` for the verb, not `target_form`. When they differ, the attested
     spelling is Uthmani and the analyzer cannot read it; `writable_note` says so. If
     `writable_form` is null, do not guess — `hand_to_human` and move on.
   - Take the other words from `candidate_words`. If you need a word that is not there,
     `lookup_word` it first: it must be analyzable and it must have a gloss.
   - **Gloss each word FROM the lexicon's glosses, not from your own translation.** The
     gate compares your gloss against the same lexicon, and a classical Quranic sense often
     differs from the modern one (حَكِيم is "physician" in that lexicon, not "wise").
   - Keep it short and meaningful: a learner's sentence, not a demonstration of range.

3. **`add_examples(root, form, [sentence])`** with `tense` and `pronoun` set, so the gate can
   check the form and not merely the root.

4. **Report the outcome.**
   - The gate passed → `record_job_outcome(job, "checked")`.
   - The gate refused → `report_failure(job, "<what exactly>")` and read
     `checks.gloss_conflicts`: those words do not mean what you claimed. Fix the gloss or
     pick a different word, then draft again. The engine parks the job itself after a few
     attempts — do not keep trying past that.

5. **Never mark it reviewed yourself.** A sentence you wrote is not one you can approve;
   that is what `/review-blind` is for, in a separate pass.

## What not to do

- Do not invent vocabulary or glosses from memory — that is the one failure this whole
  design exists to prevent.
- Do not write around a refusal by weakening the claim (dropping `tense`/`pronoun` so the
  form check is skipped). A skipped check is not a passed one.
- Do not batch a dozen sentences before recording anything: the agenda is what survives
  the session, so record as you go.
