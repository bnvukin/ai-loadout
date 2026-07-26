# AGENTS.md — guide for humans and AI agents working on Loadout

This file orients any contributor (human or AI) before they touch the code.

## What this project is

Loadout turns a fresh machine into a production-ready AI development workstation with one
command, and then keeps it healthy via a live dashboard. It is a **control center**, not a
one-off script.

## The one architectural rule

**Everything is a component in a digital twin, and every action updates the state model
first.** The lifecycle is:

```
Detected → Installed → Configured → Verified → Benchmarked → Healthy → Needs Update → Repairing → Healthy
```

Detection writes state. Installers/configurers/repairers mutate state and emit events.
The dashboard only *reads* state and *subscribes* to events. Never let the UI reach into
the system directly.

## Non-negotiables

1. **Safety.** Mutating actions are opt-in, reversible, logged, and downloaded only from
   official sources. Default to `--dry-run` / read-only.
2. **Cross-platform.** Windows-first (primary test target) but macOS/Linux must not be
   broken. Guard platform-specific code and keep pure logic OS-agnostic.
3. **Testable without a real machine.** Parse captured command output from
   `tests/fixtures/`; never hardcode a developer's paths, hostname, or usernames.
4. **Honesty.** Keep the README "Project status" table accurate. Stubs are labeled stubs.
5. **Minimal core deps.** Heavy or optional dependencies live behind extras.

## Layout

```
src/ai_loadout/
  core/       state engine (digital twin), events, lifecycle
  detect/     Layer 1 (machine) + Layer 2 (dependencies)
  models/     Layer 4 catalog + recommendation
  install/    Layer 3 runtimes + package installs
  configure/  Layers 6-8 (VS Code, Continue, MCP/agents)
  health/     Layers 10/11/13 (check, repair, doctor)
  configcenter/ config + env var + PATH discovery/editing
  dashboard/  FastAPI + WebSocket + static UI
  cli.py      command-line entry point
tests/        pytest, with fixtures/ for captured output
```

## Workflow

- `ruff check . && ruff format --check . && pytest` must pass before committing.
- Small, focused commits. Update `CHANGELOG.md` under `[Unreleased]`.
