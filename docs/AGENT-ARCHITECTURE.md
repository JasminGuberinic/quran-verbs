# Fiʿl — the factory's agent: patterns, components, and what we deliberately leave out

The engine is strong. The **operator** is the weak part: today the workflow lives in a
chat session and in the AI's head, so nothing remembers what was already tried, what
failed and why, or whether a verdict came from an independent reader. That does not
scale to 300 verbs and it is not repeatable.

The conclusion that matters: **we do not need a cleverer agent, we need a loop, durable
state, and an independent judge.** The MCP surface (9 tools) is already the right
interface — the gap is not more tools.

## What already exists (and which pattern it is)

| Pattern | Where it lives now |
|---|---|
| **Verifier-in-the-loop** (generation constrained by a programmatic check) | `fil/examples.py` — the four mechanical checks; `stages/bundle.py` refuses to ship anything unshippable |
| **Grounded context** (facts come from tools, never from the model's memory) | `fil/vocabulary.py` (the Quranic word bank), `service.lookup_word` (the lexicon's own glosses) |
| **Generator–Critic** (LLM-as-judge) | `Critique` + `service.record_critique`; `examples_to_critique` is the queue |
| **Tiered trust** (never a single "verified" bool) | `Example.tier`, and the same discipline on conjugations (`attested > consensus > generated > quarantined`) |
| **Human-in-the-loop** | `service.review_queue` for cell conflicts |
| **Adapter / Strategy** | `Conjugator` protocol, `Analyze` injection, `VoiceProvider` (audio phase) |

## What is missing

### 1. Agenda — the work queue (the actual backbone)
A durable job store: one job per **(verb, cell)** to be illustrated.

```
todo → drafted → checked → reviewed        (the happy path)
                    ↓          ↓
                  parked ← ← ← ┘           (needs a human, or gave up)
```

Each job records `attempts`, `last_failure`, and who moved it. Jobs are **idempotent**:
re-running one is safe, so a crashed or abandoned session costs nothing.

*Why first:* without it, every session starts from zero and silently repeats work that
already failed. This is the one genuinely "agentic" piece we lack.

Shape: `fil/agenda.py` (pure state transitions) + a JSON/SQLite store beside
`data/examples.json` + CLI `fil agenda`.

### 2. Brief — context assembly as a tool call
`next_job()` should hand back **everything needed to draft one sentence**, so the model
recalls nothing: the verb, the target cell, its attested form, candidate words from the
bank with their lexicon glosses, and the sentences the verb already has (to avoid
repeating a cell). One tool call in, a draft out.

*Pattern:* grounded prompt assembly. The model's only job is composition — the taste
part — never retrieval.

### 3. Independent critic
The mechanism exists; the independence does not. Every verdict so far was cast by the
same pass that wrote the sentence, and it is recorded that way in `Critique.by` on
purpose. The fix is an invocation, not more engine code: a **separate context** (Claude
Code subagent, or a different model) that receives only the sentence, its word-by-word
gloss, and the claim being made — no drafting rationale, no memory of composing it —
and returns a verdict through `critique_example`.

*Pattern:* Generator–Critic with enforced context separation. A judge who watched you
work is not a judge.

### 4. Bounded repair loop
The gate already names what is wrong (`gloss_conflicts` lists the offending words). The
agent should repair and retry — **at most N times** — then park the job with its reason.

*Pattern:* reflexion, but bounded and recorded. Unbounded self-correction is how agents
burn budget and quietly converge on nonsense.

### 5. Evals — the metric that tells us a change helped
We already produced the number by accident: before the word bank, 6 sentences yielded
2 defects; after it, 10 sentences passed first try. Formalise it:

- **first-try gate pass rate** — did grounding actually help?
- **repair attempts per accepted sentence** — is the loop converging?
- **critic rejection rate** (defect escape rate) — how much slips past the mechanics?
  This is the honest measure of the gate's real strength.
- **parked jobs, by reason** — where the pipeline actually hurts.
- **coverage** — verbs with ≥2 reviewed sentences, and which cells are illustrated.

A golden set of past sentences (including the two known-bad ones — `أَقُولُ الصِّدْقَ`
with its wrong gloss, and `أَكُونُ سَعِيدًا` which is idiomatically wrong) becomes a
regression test for the gate itself: if a future change stops catching them, we broke it.

### 6. Governor — resource limits as code, not as a note
The CAMeL constraint ("never run the full 1473-verb pass, it holds ~0.8 GB and competes
with the user's Docker") is currently a rule written in a memory file. It belongs in
code: batch sizes, a hard cap, and a refusal with a clear message.

### 7. Human handoff queue
The human does what the AI cannot: **hear** the audio, **see** the Arabic typography,
and give the linguistic content a qualified reading before release. Those are jobs too —
they belong in the agenda with a `needs_human` reason, not in someone's head.

## Deliberately NOT built

- **An LLM planner.** The work list is deterministic: verbs by frequency, cells per verb.
  There is nothing to plan; a planner would only add a way to be wrong.
- **Multi-agent debate.** One independent critic beats three agents agreeing with each
  other. Add a second lens only when we can show the first one misses a class of error.
- **RAG / a vector store.** We have an annotated corpus with exact roots, forms and
  references. Replacing exact structure with nearest-neighbour guessing would be a
  downgrade, not an upgrade.
- **An unattended long-running loop.** Nothing ships without a human asking, and pushes
  stay explicit. Autonomy is not the goal; repeatability is.
- **More MCP tools for their own sake.** Nine cover the surface. The next tool must earn
  its place by removing a decision from the model's memory.

## Build order

0. **Fix the engine gap first.** Generation is thin for hollow/hamzated verbs — `جيأ`
   has 7 conjugation cells and `رأي` 12, against 29 for sound verbs. No agent
   architecture fixes that; it would only produce half-empty cards faster.

   **Diagnosed and partly fixed (2026-08-12).** The cause was not the generator: for these
   verbs `build_verb` returned `None`, so no generator ever ran and only Quran-attested
   cells survived. Two distinct reasons:

   - *Orthography (fixed).* The Form-I present vowel is inferred by fitting a/i/u against
     an attested present form, and the comparison folded Uthmani's superscript alef into a
     full alef. Over a long vowel that mark is only a reading aid, so `يَرَىٰ` never matched
     the generator's `يَرَى` and the fit failed. Folding it correctly took the catalogue
     from 955 to **964** generatable verbs, agreement from 81.30% to **83.60%**, and
     conflicts from 421 down to **377** — `رأي`, `هدي` and `أتي` went from a handful of
     cells to a full table.
   - *No attested present at all (open, 335 verbs).* `جيأ` (278×), `ترك`, `مسس` and 332
     others are never attested in the present, so there is nothing to fit the vowel
     against. A further 164 have a present that no vowel reproduces — genuine generator
     failures on weak/doubled roots.

   **Designed fix for the 335, with the trap named.** CAMeL's lexicon can supply a present
   form (`جاءَ` → `يَجِيءُونَ`, which reveals the stem vowel `i`), so the vowel can be fitted
   against it instead of against the Quran — a *lexicon lookup*, injected as a port so the
   driver stays pure. But then Qutrub is no longer an independent witness against CAMeL: we
   *made* them agree, so calling the result "consensus" would be **circular evidence**. The
   rule must therefore be that **a generator which supplied the vowel forfeits its vote** —
   such cells are "generated" (one effective source), never "consensus". That needs the
   vowel's provenance recorded on `Verb` and honoured in `service._reconcile_entry`.
   Deferred deliberately: it only pays off under the opt-in CAMeL path, so it changes
   nothing in the default bundle.
1. **Agenda** (#1) — jobs, states, CLI, MCP `next_job` / `record_result`.
2. **Brief** (#2) — grounded context in one call.
3. **Independent critic** (#3) — the subagent invocation and the blind brief.
4. **Repair loop** (#4) — bounded, recorded.
5. **Evals** (#5) — the golden set and the five numbers.
6. **Governor** (#6) and **human handoff** (#7).

Then, and only then, mass content: the loop makes 300 verbs a batch job instead of 300
conversations.

## Where this lives in the existing layering

This is **Layer C** of `STUDIO-ARCHITECTURE.md` — the Skills layer that was planned and
never built. The engine (Layer A) and the MCP surface (Layer B) stay as they are:

- **engine** — agenda state, brief assembly, evals, governor (testable, no LLM involved)
- **MCP** — the tools that expose them
- **Skills** — the recipes: `/next-sentence`, `/review-blind`, `/report-metrics`
- **hooks** — the guardrails that cannot be talked out of (no push without a human)

The agent is not a new component. It is the loop that finally closes around the ones we
already have.
