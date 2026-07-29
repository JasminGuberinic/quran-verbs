# Code quality standard — NON-NEGOTIABLE for this project

This is a religious-education app: correctness is sacred and the code must be
top-tier. Every change follows these principles.

## Architecture
- **Clean / hexagonal domain architecture.** Dependencies point inward. The
  domain (models, ports) is pure — it never imports a framework, a tool, or I/O.
  Concrete things (ffmpeg, Qutrub, SQLite, SwiftUI) live at the edges as adapters.
- **Composition root:** one place wires concrete classes; everything else depends
  on interfaces/ports (`Protocol`).
- **Recognize and apply design patterns where they fit** — Strategy/Provider
  (pluggable voice), Adapter (tool wrappers), Pipeline (build stages), Composition
  Root. Never force a pattern; never over-engineer speculatively.

## Clean code
- **Reads like a book.** Top-down: high-level methods read as prose; details live
  in small well-named helpers. Comments explain **why**, never restate the code.
- **Intention-revealing names.** No abbreviations, no `tmp`/`data`/`x`. Methods are
  verbs, classes are nouns, booleans read as predicates (`is_…`, `has_…`).
- **Bite-size methods** — single responsibility, one level of abstraction each.
- **Guard clauses / early returns.** No deep nesting. Avoid `else` when a guard
  makes it unnecessary. If you see many nested `if`s, refactor.
- **Fail fast.** Validate at boundaries; raise clear, specific errors immediately.
- **Immutability by default** — frozen dataclasses, no shared mutable state.
- **Functional techniques** where they clarify — pure functions, comprehensions,
  map/filter, separating pure decision logic from side-effecting I/O (so logic is
  unit-testable without the tool).
- **Full type hints.** English throughout.

## Flexibility
- Be **generic/pluggable where it earns its keep** (voice providers, analyzer
  ports) — driven by a real second case, not speculation.

## Testing (correctness is sacred)
- **Golden tests** encode known-correct Arabic forms as ground truth.
- **Structural invariants** hold for every verb we ever add.
- **Pure logic is separated from I/O** so it tests without external tools.
- **QA gates fail the build** — a silent/clipped/missing clip must never reach a
  learner. No asset ships that hasn't passed every gate.
- Final release also gets **human scholar review** of the linguistic content;
  tests guard against regressions and enforce structure, not scholarly perfection.

Anything that violates these gets refactored before it lands.
