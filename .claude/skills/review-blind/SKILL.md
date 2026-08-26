---
name: review-blind
description: Judge practice sentences independently, in a context that had no part in writing them. Use when reviewing Fiʿl practice sentences, clearing the blind review queue, or when the user asks for an independent read, a second opinion, or "review the sentences".
---

# Judge the sentences independently

The mechanical gate proves the Arabic is real and the verb is in the right form. It cannot
tell whether a sentence is natural, whether the grammar beyond the verb holds, or whether
the translation says what the Arabic says. That is this pass — and its only value is that
it owes nothing to the pass that wrote the sentences.

## Why this must run in a separate context

A reader who knows the gate passed a sentence, or who remembers choosing its words, is not
a witness. So `sentences_to_review_blind` deliberately withholds the check results, the
drafter's reasoning, and the current tier: you get the Arabic, the word-by-word gloss, and
the claim being made. Judge that.

**Delegate this to a subagent** (or a different model) rather than doing it in the session
that drafted. If you drafted any of these sentences yourself, say so in `by` and pass
`independent=false` — a false claim of independence turns the whole layer into decoration.

## The loop

1. **`sentences_to_review_blind()`** — the queue. A sentence stays here until an
   independent verdict exists, even if the drafting pass already approved it.

2. **Judge each on three axes**, separately, and refuse if any fails:
   - `grammar_ok` — the whole sentence: case endings, agreement, word order.
   - `translation_ok` — the English and Bosnian, *and each word's own gloss*. A rendering
     that contradicts its own gloss is a defect even when both are defensible alone.
   - `verb_usage_ok` — is the verb used as the language actually uses it, in the claimed
     tense and person? A form can be flawless and still teach a wrong habit: MSA drops the
     present copula, so أَكُونُ سَعِيدًا is morphologically perfect and wrong to teach.

3. **`critique_example(..., independent=true)`** with a concrete note. When refusing, say
   what would fix it — the note is what the repair is drafted from.

4. **Do not repair anything here.** Judging and fixing in one pass is how a reviewer talks
   themselves into approving their own work. Refuse, and let `/next-sentence` redraft it.

## Reading the result

`metrics()` reports the **reader rejection rate** — the share of sentences that passed the
mechanics and were then refused here. That number is the honest measure of what the
automatic layers miss. If it is ever 0%, assume the review is not working rather than that
the pipeline is perfect.
