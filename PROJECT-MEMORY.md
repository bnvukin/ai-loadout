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
- (subsequent batches appended as delivered)

## Open questions / future

- Bootstrap entry scripts that install Python itself (the true "one command").
- Real end-to-end install test in a disposable VM/sandbox before recommending mutating runs.
