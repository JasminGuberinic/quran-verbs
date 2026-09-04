# Agentic engineering, as practised in this repo

Every pattern below is in the code, and each one is here because something went wrong
without it. Read it as a field guide rather than a taxonomy: what the pattern solves, where
it lives, what breaks in its absence, and how it fails once you have it.

## The one idea everything else serves

**A verifiable check beats a better prompt.** The model composes; something that cannot be
talked round decides whether the result is acceptable. Every pattern here is either a way to
make that check possible, a way to keep it honest, or a way to know when it is not enough.

The corollary is uncomfortable and worth accepting early: *the parts a model does well are
rarely the parts you can verify.* Composition, taste and idiom are exactly what no analyzer
can judge — so the design has to route them to a different kind of judge, not pretend the
analyzer covers them.

---

## 1. Grounded context — hand over facts, never ask for recall

**Where:** `service.brief_for` · `fil/vocabulary.py` · `service.lookup_word`

A brief gives the drafter the exact form to use, words the Quran actually contains, and each
word's meaning *according to a lexicon we did not write*. The model's only job is
composition.

**Without it:** the model invents vocabulary and glosses from memory, and the gate spends its
life catching mistakes that never needed to be made. Before the word bank, 6 sentences
carried 2 defects; after it, 10 passed on the first attempt.

**How it fails:** the brief grows until it is the whole corpus. Cap it, and prefer *vetted*
candidates (`_vetted_words` drops anything the analyzer cannot read or gloss) over more of
them. A brief that offers something the gate will reject is worse than a short one.

## 2. Verifier-in-the-loop — the check is code, not a prompt

**Where:** `examples.check_example` (four mechanical checks) · `stages/bundle.py` (the gate
that refuses to ship)

**Without it:** you are grading your own homework with the same instrument that wrote it.

**How it fails:** by being trusted beyond its reach. Our checks prove the Arabic is real and
the verb is in the claimed form. They say nothing about idiom. `أَكُونُ سَعِيدًا` passes every
one of them and still teaches a wrong habit, which is why it sits in the golden set as a case
that must *keep passing*.

## 3. Tiered trust — never one boolean

**Where:** `Example.tier` (`reviewed > checked > rejected > unchecked`) ·
`ReconciledCell.source` (`attested > consensus > generated > quarantined`)

A single `verified` flag forces every distinct level of evidence into one bit, and the bit is
always read optimistically downstream.

**Without it:** "verified" means "some check ran", and nobody remembers which.

**How it fails:** tier inflation. We hit this exactly: a sentence the *drafting pass* approved
was labelled `reviewed`, which read as "someone checked it". The fix was a second, narrower
predicate — `independently_reviewed` — rather than redefining the old one.

## 4. Generator–Critic, with separation of duties **enforced**

**Where:** `service.blind_reviews` · `Critique.independent` · `service.SelfReviewError`

The critic gets the sentence, its glosses and the claim — and deliberately *not* the check
results, the drafter's reasoning, or the current tier. A reader who knows the machine passed
it is no longer a witness.

**Without it:** the review is theatre. Ours refused **5 of the first 16** sentences: two
English collocations that are not English, an imperfective verb unidiomatic with a bare
object, a gloss right in the dictionary and wrong in the sentence, and a translation
contradicting its own gloss.

**How it fails:** the author reviews their own work. So the engine refuses it —
`record_critique` raises when a verdict claims independence and `by` matches `drafted_by`. A
rule that lives in a document is a suggestion; the same rule in a constructor is a mechanism.

## 5. Make illegal states unrepresentable

**Where:** `Critique.__post_init__` · `agenda._ALLOWED` (`reviewed` is terminal)

You cannot construct a verdict that is approved while its grammar check failed, and you
cannot refuse without saying why. You cannot reopen an approved sentence by accident.

**Without it:** "approved with reservations" — the summary says yes, the detail says no, and
only the summary travels downstream.

**How it fails:** rarely, and that is the point. The cost is that you must model the domain
honestly enough to know which combinations are illegal.

## 6. Durable state **and** append-only history — they are not the same thing

**Where:** `fil/agenda.py` (state) · `fil/journal.py` + `journal_store.py` (history)

This is the pattern that cost us a real bug, so it is worth the space.

The factory measured how often a reader caught something the machine had missed, by reading
the current sentences. But repairing a refused sentence **replaces** it — so the moment a
defect was fixed, the evidence it had ever existed vanished. The metric reported a flawless
**0%** immediately after five genuine defects were found and repaired.

The mistake was architectural: **state was being used as history.** A store of "what is true
now" cannot answer "what happened", and every attempt to squeeze the second from the first
produces numbers that flatter whoever asks.

So: the agenda holds one overwritable row per cell; the journal is append-only JSONL, one
line per event, never edited. `evals.measure` takes both, and takes the historical questions
from the journal. The true rate is **23.8%**.

**How it fails:** an event log grows forever and nobody reads it. Keep the kinds few, make
each one answer a question somebody actually asks, and derive metrics from it rather than
storing them.

## 7. Bounded repair, and a stop-loss above it

**Where:** `agenda.after_failure` (`MAX_ATTEMPTS`) · `governor.stop_loss`

Two different limits, and you need both. The per-job budget stops one cell from consuming a
session. The stop-loss stops the *batch*: a hundred cells each failing once never trips a
per-job budget, yet the pattern means something upstream is broken.

**Without them:** an agent grinds, spends, and converges on something plausible.

**How it fails:** by hiding the reason. Always park with the failure recorded, or the next
session repeats the attempt from nothing.

## 8. Leases, not locks — concurrency without a supervisor

**Where:** `agenda.claim` / `is_claimed` / `released` (`LEASE_SECONDS`)

Two agents against the same repo will otherwise both take the same "next" job, and one of
the two sentences is silently discarded.

**Why a lease:** nothing in the system can tell whether a worker died. A lock would need a
human to release it; a lease simply expires.

**How it fails:** too short and two workers duplicate anyway; too long and a dead session
freezes a cell. Ours is 15 minutes because a drafting pass takes seconds.

## 9. A resource governor, where the cost is declared not guessed

**Where:** `fil/governor.py` · `Conjugator.is_heavy`

One generator holds close to a gigabyte. The rule "never run it over the whole catalogue"
lived in a note for weeks. A note is advice, and an agent working a long agenda will
eventually take the shortcut because nothing stops it.

Now the generator declares its own cost and the run is refused **with instructions**: run it
in batches, or use the light one. A refusal that does not say what to do instead just gets
worked around.

## 10. Evals and a golden set — the difference between "tests pass" and "it still works"

**Where:** `fil/evals.py` · `data/golden_sentences.json` · `fil evals`

Five numbers, and the one that matters most is the **reader rejection rate**: what got past
the mechanics and was caught by a human. *If that number is ever 0%, suspect the review, not
the gate.*

The golden set pins the gate itself with cases whose verdict we already know — including both
sentences that were genuinely wrong. One must still be refused. The other must still **pass**,
because it is morphologically perfect and only a reader can know it teaches a bad habit.
Encoding that boundary is what stops a future "simplification" from quietly becoming more
agreeable.

**How it fails:** a rate computed from no data reported as `0.0%`. Ours returns `None` and
prints "no data", because zero and unknown are different claims.

## 11. Human handoff as a queue, not an apology

**Where:** `service.hand_to_human` / `handoff_queue` · `agenda.NEEDS_HUMAN`

Hearing whether audio is clean, seeing whether Arabic renders correctly, and a qualified
reading of the language are jobs with a *different worker*, not gaps in the pipeline. They
are tracked, and told apart from "we gave up".

## 12. Tool descriptions are an API — so test them

**Where:** `tests/test_tool_contracts.py`

A human reading a badly documented function can read its body. An agent cannot: the
description and the argument list are the entire contract. A tool whose docstring omits an
argument will be called wrongly, silently, and repeatedly.

So every tool must have a real description, every argument must appear in it, and every tool
that writes state must say so. It fails the build like a type error, because it is one.

---

## The failure modes to expect

A checklist earned rather than imagined. Every one of these happened here.

1. **Self-approval.** The pass that produced the work signs it off. → Enforce separation in
   code, and record who did what.
2. **Erased evidence.** A repair overwrites the defect, and the metric improves because the
   proof is gone. → History must be append-only.
3. **Partial dependency injection** — the worst of the four, because it *looks* isolated. Our
   tests redirected the sentence store and the agenda, but the journal path was defaulted at
   the write, so the suite wrote its fixtures into the real history and moved a live metric
   from 23.8% to 15.6%. → Thread the path from every caller; never default it deep inside.
4. **Circular evidence.** Two "independent" generators, where one was tuned from the other,
   agreeing loudly. → If a generator supplies an input, it forfeits its vote.
5. **Overclaiming labels.** `verified`, `reviewed`, `validated` — each drifts to mean "some
   check ran". → Name the specific check, or tier it.
6. **Silent truncation.** Dropping the tail of a batch and reporting success. → Say what was
   dropped, always (`stages/bundle.py` prints every sentence it holds back).
7. **A check that cannot fail.** A gloss comparison where both sides come from the same
   place; a gate skipped because a field was left unset. → A skipped check is not a passed
   one, and `None` must never be treated as `True`.

## What we deliberately did not build

- **An LLM planner.** The work list is deterministic — verbs by frequency, cells per verb.
  A planner would only add a way to be wrong.
- **Multi-agent debate.** One genuinely independent critic beat sixteen self-assessments.
  Add a second lens when you can show the first misses a class of error, not before.
- **RAG over the corpus.** We have exact roots, forms and references. Replacing exact
  structure with nearest-neighbour guessing is a downgrade wearing a fashionable name.
- **An unattended loop.** Nothing ships without a person asking. Repeatability is the goal;
  autonomy is not.

## Where to start reading

| Question | File |
|---|---|
| What does the factory owe, and what happened? | `agenda.py`, `journal.py` |
| What does a drafter get handed? | `service.brief_for`, `vocabulary.py` |
| What decides whether a sentence is acceptable? | `examples.py`, `glosses.py` |
| Who is allowed to approve it? | `service.record_critique`, `Critique` |
| How do we know any of this is working? | `evals.py`, `data/golden_sentences.json` |
| What stops it from hurting the machine? | `governor.py` |
| How is it driven? | `mcp/server.py`, `.claude/skills/` |

The layering itself is in `STUDIO-ARCHITECTURE.md`, and the component-by-component plan with
what remains is in `AGENT-ARCHITECTURE.md`.
