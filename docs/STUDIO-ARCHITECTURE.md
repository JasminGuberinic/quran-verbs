# Fiʿl — the content factory as a real, AI-operated application

The end-user products are **native iOS + Android apps** (later phase). This document
is about the **factory** that produces their content: it must be a real, professional
application — not a pile of scripts — and it is designed to be **operated primarily by
an AI agent (Claude)**, because that is who will actually run it. The human does only
what the AI cannot: *hear* the audio and *see* the Arabic typography.

## Design principle
**AI-first operation.** Every capability is exposed as a structured, machine-callable
tool (MCP) and encoded as a repeatable workflow (Skills). Human interaction is the
exception (sensory QA), not the rule.

## Layers (each a clean "lego brick")

### 1. `fil-core` — the engine (single source of truth)
Python package, clean/hexagonal architecture (pure domain + adapters + composition
root), installable via `pyproject.toml` with a `src/` layout, fully tested, CI-gated.
Contains the whole pipeline: QAC ingest → catalogue → oracle → generate → reconcile
→ audio → QA → package. Pure decision logic is separated from I/O so it tests without
external tools.

### 2. `fil` — the CLI
A thin entry point over the core (`fil ingest|coverage|build|...`). For humans, CI,
and scripts. Not the primary interface.

### 3. `fil-mcp` — the MCP server (Claude's primary interface)
Exposes the factory as MCP tools so Claude operates it conversationally, across
sessions, from Claude Code or Claude Desktop. Planned tools:
- `get_verb(root, form)` → card + confidence-coloured conjugation table + exact ayāt
- `list_verbs`, `add_verb`
- `run_stage(stage)`, `build_bundle`
- `coverage_report`, `review_queue` (quarantine: attested vs generated)
- `verify_verb(root, form)` → reconcile (+ Whisper ASR later) → structured verdict
All results are structured JSON so the agent parses them cleanly.

### 4. Claude Code Skills — repeatable factory workflows
`/add-verb`, `/review-quarantine`, `/rebuild-bundle`, `/qa-audio` — the recipes that
turn "add a verb → rerun" into consistent, one-command operations the AI runs the
same way every time.

### 5. Studio (thin web UI) — human sensory QA only
The one place a human is needed: **play the audio** (catch crackle / wrong sound) and
**view the rendered Arabic cards/typography**. Everything else the AI does. Built with
proper libraries (React + TypeScript + Vite); can be wrapped as a desktop app (Tauri)
later. It reads the same core outputs — it never contains logic of its own.

## Output
A single read-only `content.sqlite` bundle (+ audio assets), integrity-checked. The
native apps only *read* it; they compute nothing.

## Build order
A. Restructure the engine into `fil-core` (real installable package, clean structure,
   tests green, CI).
B. `fil-mcp` server over core (the AI control surface).
C. Claude Code Skills for the workflows.
D. Studio web UI for audio/visual QA.
(Glosses source and release-quality audio are separate content phases.)
