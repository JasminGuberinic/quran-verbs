---
name: report-metrics
description: Report how the Fiʿl factory is doing and re-check the gate against the golden set. Use when asked for status, coverage, progress, whether a change helped, or before and after any change to the sentence gate.
---

# Report how the factory is doing

Two different questions, and it is worth keeping them apart.

## Is the pipeline working?

`metrics()` — or `fil evals` for the printed version:

- **first-try gate pass rate** — did grounding the drafter in the word bank and the lexicon
  actually work? This is the number that moved when the bank was built.
- **drafts per accepted sentence** — is the repair loop converging or thrashing?
- **reader rejection rate** — the share of verdicts where a reader refused a sentence the
  mechanics had passed. **This is the honest measure of what the automatic layers miss.**
  If it reads 0%, suspect the review rather than celebrate the gate.
- **parked** — where the pipeline hurt enough that we stopped; each parked job says why.
- **distinct cells illustrated** — what a learner can actually be shown.

A rate of `None` means nothing has happened yet. Report it as "no data", never as 0%.

Refusals are counted on the agenda rather than in the sentence store, because repairing a
refused sentence replaces it — read the store alone and the factory would be grading itself
on evidence it had just erased.

## Does the gate still work?

`fil evals` also re-runs the gate over the **golden set**: sentences whose verdict we
already know, including two that were genuinely wrong — a gloss the lexicon does not
support, and a sentence that is morphologically perfect but teaches a wrong habit. A
differing verdict is a regression, and the stage exits non-zero when one appears.

Run this **before and after** any change to `examples.py`, `glosses.py` or the analyzer
wiring. "The tests pass" is not the same claim: the golden set is what notices when the
gate has quietly become more agreeable.

## Reporting it to a person

Give the numbers, then say what they mean and what you would do about it. Do not round a
bad number into a good sentence — a high rejection rate is information about the gate, not
a failure to apologise for.
