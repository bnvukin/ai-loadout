# Project Memory — Loadout

A running log of decisions, rationale, and state so the project can be picked up at any
time without re-deriving context. Newest entries at the top.

## Key decisions

- **Name:** `Loadout` (repo/package `ai-loadout`). "AI Bootstrap" and "AI Forge" were both
  already taken across GitHub/PyPI/npm; short brandable names (à la Homebrew/Scoop) are the
  proven pattern for installer tools. Hardware "profiles" map naturally to curated
  "loadouts".
- **Language/stack:** Python 3.9+ core (portable, great for system introspection and
  subprocess orchestration). Dashboard = FastAPI + WebSocket serving a dependency-free
  vanilla-JS/CSS SPA (works offline, no build step, easy CI).
- **Architecture:** digital-twin state engine is the single source of truth; every layer
  and the dashboard plug into it. Component lifecycle is a shared state machine.
- **Safety:** read-only / dry-run by default; official sources only; checksum verification;
  three trust levels for config edits.
- **Distribution:** MIT-licensed public repo. Third-party tools are installed from official
  sources, never bundled.

## Build log

### Session 1 — 2026-07-26
- Extracted the full product brief and turned it into a 20-layer + Config-Center plan.
- Verified toolchain on the dev machine: Python 3.12/3.14, Git, GitHub CLI, Node 24,
  VS Code, winget, Ollama present; Docker absent (a good real test case for detection).
- Confirmed remote `github.com/bnvukin/ai-loadout` (public, empty).
- Batch 1: repo scaffolding — license, packaging, docs, hygiene.
- Batch 2: core state engine (digital twin) + event bus + lifecycle + CLI skeleton.
- Batch 3: Layer 1 machine validation (`loadout scan`) with pure parsers + fixtures.
- Batch 4: Layer 4 model catalog + hardware-aware recommendation (`loadout models`).
- Batch 5: Layer 2 dependency manager (`loadout deps`) — detect + version decision tree.
- Batch 6: Layer 3 AI runtime/editor detection (`loadout runtimes`) + local model discovery.
- Batch 7: Layers 10 & 13 health check + AI doctor (`loadout health` / `loadout doctor`) —
  twin + live probes → actionable issues with plain-language explain/fix/why/restart.
- Batch 8: Config Center (`loadout config`) — discover well-known config files across OSes,
  inspect AI env vars, analyse PATH (missing/duplicates); secrets redacted, read-only.
  Trust-gated, backup-first edits live in `config.edit` (foundation for the dashboard).
- Batch 9: dashboard backend (`loadout dashboard`) — FastAPI over the twin (read APIs +
  scan trigger), background Orchestrator running detection layers off-thread, and a `/ws`
  WebSocket bridging the EventBus to the browser. Web stack is the `[dashboard]` extra.
- Batch 10: dashboard frontend — dependency-free vanilla-JS SPA (no build step) with
  Overview/Components/Models/Config/Activity views, live WebSocket updates, a Rescan
  button and per-task progress chips. Verified live: assets serve, scan runs end-to-end.
- Batch 11: Layer 18 profiles + planner (`loadout plan`) reconciling a profile/capabilities
  against the twin into a dry-run install plan (real package-manager commands, hardware-aware
  model pick), plus `bootstrap.ps1`/`bootstrap.sh` one-command entry scripts. Verified live:
  `plan --profile ml-engineer` correctly skipped present tools and emitted winget/pip/ollama steps.
- Batch 12: CI — GitHub Actions (`.github/workflows/ci.yml`): ruff lint/format gate + pytest
  matrix (windows/macos/linux x py3.9/py3.12) + CLI smoke test. README CI badge added.
  First run verified green (all 7 jobs) via `gh run watch`.
- Batch 13: docs polish — README "Commands available today" table + accurate profile names,
  CLI checklist marked complete. 88 tests green locally and in CI.

## Delivery snapshot (end of session 1)
Shipped, tested (88 tests), and CI-green across 3 OSes: Layers 1-4, 10, 13, 18, the Config
Center, and the full live dashboard (backend + SPA), plus profiles/planner and bootstrap
scripts. Everything is read-only / dry-run; actual mutating installs (via the orchestrator)
are the next major piece, followed by Layers 5-9, 11-12, 14-17, 19-20.

- (subsequent batches appended as delivered)

## Open questions / future

- Bootstrap entry scripts that install Python itself (the true "one command").
- Real end-to-end install test in a disposable VM/sandbox before recommending mutating runs.
