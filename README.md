<div align="center">

# Loadout

**One command to turn any Windows, macOS, or Linux machine into a production-ready AI development workstation.**

[![CI](https://github.com/bnvukin/ai-loadout/actions/workflows/ci.yml/badge.svg)](https://github.com/bnvukin/ai-loadout/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![Status: Alpha](https://img.shields.io/badge/status-v0.1.0%20alpha-orange.svg)](#project-status)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](./CONTRIBUTING.md)

</div>

**Status: v0.1.0 — all 20 layers + product pillars implemented.** Install via
`pip install ai-loadout[dashboard]` (after PyPI publish) or bootstrap scripts; run everything
from `loadout dashboard` on Windows, macOS, or Linux. See [Known limitations](#known-limitations).

---

Every developer loses hours doing the same first-hour ritual on every new machine:
install Python, Node, Docker, Git, VS Code, Ollama, pull models, wire up Continue/MCP,
fix `PATH`, repeat. **Loadout does it once, correctly, and then keeps watching.**

```bash
# The whole idea
loadout
# coffee -> come back -> a working AI workstation + a live dashboard
```

Loadout is not "an installer for tool X". It is an **AI workstation control center**:
it validates your machine, recommends models that actually fit your hardware, installs
and configures the stack, verifies everything, and then opens a **live dashboard** that
stays useful long after setup.

## Why Loadout is different

Most setup scripts are a pile of `if not installed: install`. Loadout is built around a
single idea:

> **Your machine is a digital twin.** Every component — Git, Python, Docker, Ollama,
> VS Code, a local model, a config file, an environment variable — is an object with the
> same lifecycle:

```
Detected → Installed → Configured → Verified → Benchmarked → Healthy → Needs Update → Repairing → Healthy
```

Every action updates the state model first; the dashboard is just a live view of that
state. That is what turns "a bunch of scripts" into a platform you can extend.

## Highlights

- **Zero-interrupt install** — answer everything up front (or accept smart defaults),
  then never get interrupted. Credentials/logins are deferred to a post-install
  Connections page, never blocking the install.
- **Hardware-aware model recommendations** — not a static list. A comparison table
  (coding / reasoning / speed / RAM / offline) plus *"on your RTX 4070 + 32 GB, Qwen3 8B
  will do ~75 tok/s, ~9.8 GB, 64K context."*
- **Live, actionable dashboard** at `http://localhost:8421` — overall health, components,
  models, config, and a live event stream. Anything that isn't green is fixable *from the
  browser*: one-click Install/Update/Repair with a confirm step and streaming logs, a
  "Why do I need this?" explainer per component, one-click model pulls, and a per-component
  re-detect that flips the badge green.
- **Config Center** — every scattered config (`.continue`, `.ollama`, `.gitconfig`,
  VS Code `settings.json`, `PATH`, and **every** environment variable) discovered,
  categorized, searchable. Open a file, edit it, and save — SAFE files save directly,
  ADVANCED/EXPERT require typing `CONFIRM`/`EDIT`, and every write is backed up first.
- **Safety first** — official package-manager sources in command templates; trust posture
  report (`loadout security`); SHA256 helpers for direct downloads; config edits
  trust-gated (`CONFIRM` / `EDIT`) with per-file backup + global snapshots. See
  [Safety, privacy & legal](#safety-privacy--legal).
- **Profiles & Capabilities** — pick *ml-engineer* or *agentic-coder* instead of ticking
  50 tools; each expands transparently into the underlying components (`loadout plan`).

## Install

**From PyPI** (once published — see [RELEASING.md](./RELEASING.md) for maintainer steps):

```bash
pip install ai-loadout[dashboard]
loadout --version
```

The `[dashboard]` extra installs FastAPI + Uvicorn so `loadout dashboard` works. Core-only
(`pip install ai-loadout`) is enough for scan/plan/health/doctor and all read-only CLI commands.

**From source** (development):

```bash
git clone https://github.com/bnvukin/ai-loadout.git
cd ai-loadout
pip install -e ".[dashboard,dev]"
```

**From a built wheel** (local verify before release):

```bash
python -m pip install build twine
python -m build
twine check dist/*
pip install dist/ai_loadout-*.whl[dashboard]
loadout --help
```

**Bare machine?** Use the bootstrap scripts — they install Python (winget / Homebrew / apt),
then Loadout, then run the first scan:

```powershell
./bootstrap.ps1 -Dashboard     # Windows
```

```bash
./bootstrap.sh --dashboard     # macOS / Linux
```

## Quick start

> ⚠️ **Alpha (v0.1.0).** All 20 layers are implemented; read [Project status](#project-status)
> for honest partials. Nothing mutating runs without your confirmation from the dashboard.

```bash
# 1. Install
pip install ai-loadout[dashboard]          # PyPI (after first release)
# — or — pip install -e ".[dashboard]"   # from a git clone

# 2. Scan your machine (read-only)
loadout scan
loadout self-test                   # install confidence check (exit 0 = PASS)
loadout plan --list
loadout plan --profile ml-engineer        # dry-run install plan

# 3. Open the live dashboard — install/fix from the browser with confirm + logs
loadout dashboard
# → http://localhost:8421 — Rescan, Profiles → Install profile, Connections, Settings
```

<details>
<summary>Alternative: clone from GitHub (same as before)</summary>

```bash
git clone https://github.com/bnvukin/ai-loadout.git
cd ai-loadout
pip install -e ".[dashboard]"
loadout scan
loadout dashboard
```

</details>

### Commands available today

All of these are implemented and covered by the cross-platform test matrix. The **CLI** is
read-only / dry-run — nothing on your machine changes from the command line. The
**dashboard** (`loadout dashboard`) can now *act* — install/upgrade/repair components, pull
models, and edit config files — but only after an explicit confirmation, with everything
logged to `install.log`.

| Command | What it does |
|---------|--------------|
| `loadout scan` | Detect machine + toolchain + AI runtimes into the digital twin |
| `loadout deps` | Developer toolchain with install/upgrade/skip decisions |
| `loadout runtimes` | Ollama / VS Code / Continue / agent CLIs + local models |
| `loadout models` | Hardware-aware model comparison table with tok/s + RAM estimates |
| `loadout health` / `loadout doctor` | Actionable issues, then plain-language explanations |
| `loadout self-test` / `loadout doctor --self-test` | Install confidence check (imports, dashboard, scan; exit 1 on fail) |
| `loadout config [--show KEY \| --env \| --path]` | Config Center: files (redacted), env vars, PATH |
| `loadout security` | Trust / integrity posture (official sources, package managers) |
| `loadout diagnostics` | Bundle redacted logs + state into `~/.ai-loadout/diagnostics/` |
| `loadout backup` / `loadout backup --list` | Create or list global config snapshots |
| `loadout restore <id> --confirm RESTORE` | Restore a snapshot (destructive; dashboard preferred) |
| `loadout download <url> [--dest PATH] [--sha256 HEX]` | Dry-run direct download plan (official-source check) |
| `loadout update` | Check Loadout self-update (PyPI) + component upgrades (read-only) |
| `loadout benchmark` / `loadout benchmark --latest` | Run or show latest CPU/disk/inference benchmark |
| `loadout vscode` | Preview merged VS Code / Cursor `settings.json` (read-only) |
| `loadout continue` | Preview generated Continue `config.yaml` (read-only) |
| `loadout agents` | Preview starter MCP config + agent folder scaffold (read-only) |
| `loadout new --list` / `loadout new <template> <name> [--dir]` | List or scaffold a project template (creates new dir; `--force` to overwrite) |
| `loadout offline` | Connectivity probe + offline capabilities + download cache report |
| `loadout telemetry --status` | Telemetry opt-in status (local-only; disabled by default) |
| `loadout plan --list` / `loadout plan --profile <key>` | Dry-run install plan for a profile |
| `loadout dashboard` | Live web dashboard at `http://localhost:8421` |

## The 20 layers

Loadout is organized as layers. Each layer plugs into the same state model.

| # | Layer | What it does |
|---|-------|--------------|
| 1 | Machine Validation | OS, CPU, RAM, GPU/VRAM, disk, internet, admin, virtualization, existing installs |
| 2 | Dependency Manager | Detect Git/Python/Node/uv/Docker/WSL/winget/choco/brew/CUDA and decide install vs upgrade vs skip |
| 3 | AI Runtime | Ollama, Open WebUI, Continue, Claude Code, Codex CLI, Gemini CLI, ... |
| 4 | Model Recommendation | Hardware-aware model table + tokens/sec, memory & load-time estimates |
| 5 | Download Manager | Resume, retry, verify, throttle model/tool downloads |
| 6 | VS Code Configuration | Extensions + `settings.json`, keybindings, tasks, profiles |
| 7 | Continue Configuration | Auto-generate config from detected providers/models |
| 8 | Agent Configuration | MCP servers, memory/prompt folders, workspace structure |
| 9 | Project Templates | FastAPI, Next.js, Python Agent, RAG, LangGraph, MCP Server, ... |
| 10 | Health Check | Verify every component and surface fixes |
| 11 | Auto Repair | Repair PATH/permissions/services/Docker/Ollama in one click |
| 12 | Benchmark | CPU/GPU/disk/inference, tokens/sec, recommended model |
| 13 | AI Doctor | Explain slow inference, wrong CUDA, low RAM ... in human language |
| 14 | Security | SHA256, signatures, official URLs only, no unofficial mirrors |
| 15 | Logging | `install.log`, `benchmark.log`, `system.json`, `diagnostics.zip` |
| 16 | Update Manager | Check / upgrade / rollback |
| 17 | Backup | Back up configs & settings; restore later |
| 18 | Profiles | Student / AI Research / ML Engineer / Agent Developer / Minimal / Offline |
| 19 | Offline Support | Cache installers, mirror repos, install without internet |
| 20 | Telemetry (opt-in) | Anonymous, opt-in aggregate stats only |

Plus the **Config Center** pillar (discover/edit every config, env var and `PATH` entry
from one place) and **continuous health monitoring**.

See [Project status](#project-status) for what is functional today vs. planned.

## Architecture

```
Machine (digital twin)
├── Hardware            ├── Configurations       ├── Benchmarks
├── Operating System    ├── Environment Vars     ├── Logs
├── Installed Software  ├── Services             ├── Backups
├── AI Runtimes         ├── Dependencies         ├── Updates
├── Models              ├── Health               └── Repair Actions
```

- `ai_loadout.core`  — the state engine (digital twin), events, lifecycle.
- `ai_loadout.detect` — Layer 1 (machine detection).
- `ai_loadout.deps` / `ai_loadout.runtimes` — Layers 2 & 3 (toolchain + AI runtimes).
- `ai_loadout.models` — Layer 4 (catalog + hardware-aware recommendation).
- `ai_loadout.health` — Layers 10 & 13 (health check + AI doctor).
- `ai_loadout.config` — Config Center (discover / read / trust-gated edit / env + PATH).
- `ai_loadout.vscode` — Layer 6 (settings merge, extension install commands).
- `ai_loadout.continue_cfg` — Layer 7 (Continue `config.yaml` generation).
- `ai_loadout.agents` — Layer 8 (MCP starter + workspace folders).
- `ai_loadout.templates` — Layer 9 (project scaffolds).
- `ai_loadout.offline` — Layer 19 (connectivity probe, offline gating, download cache).
- `ai_loadout.telemetry` — Layer 20 (opt-in local-only anonymous stats).
- `ai_loadout.connections` — Connections pillar (credential presence guidance).
- `ai_loadout.actions` — Phase 2 execution engine (build / run / repair, streamed).
- `ai_loadout.dashboard` — FastAPI + WebSocket live UI at `:8421`.
- ... (more modules added per layer)

## Project status

Loadout is in **active alpha**. This table is kept honest — it reflects what actually
works, not the vision.

| Area | Status |
|------|--------|
| Repo scaffolding, packaging, license | ✅ done |
| Core state engine (digital twin) | ✅ done |
| Layer 1 — machine detection (`loadout scan`) | ✅ done |
| Layer 4 — model recommendation (`loadout models`) | ✅ done |
| Layer 2 — dependency manager (`loadout deps`) | ✅ done |
| Layer 3 — AI runtime detection (`loadout runtimes`) | ✅ done |
| Layers 10 & 13 — health check + AI doctor (`loadout health` / `loadout doctor`) | ✅ done |
| Config Center — discover/read configs + env + PATH (`loadout config`) | ✅ done |
| Live dashboard — API + WebSocket + orchestrator + SPA UI (`loadout dashboard`) | ✅ done |
| Layer 18 — profiles + dry-run install plan (`loadout plan`) | ✅ done |
| Bootstrap scripts (`bootstrap.ps1` / `bootstrap.sh`) | ✅ done |
| **Phase 2 — action engine (install/upgrade/pull/repair + streaming logs)** | ✅ done |
| **Phase 2 — actionable dashboard (fix/install/pull/edit from the browser)** | ✅ done |
| Layer 11 — auto-repair (Ollama/Docker, PATH dedupe, Loadout perms) | ✅ done |
| Config editing from the dashboard (trust-gated + backup) | ✅ done |
| Layer 14 — security / integrity (`loadout security`, `/api/security`) | ✅ done |
| Layer 15 — logging & diagnostics (`system.json`, `loadout diagnostics`) | ✅ done |
| Layer 17 — global backup / restore (`loadout backup`, dashboard restore) | ✅ done |
| Layer 5 — download manager (resume/retry/verify, dashboard confirm) | ✅ done |
| Layer 16 — update manager (`loadout update`, dashboard Updates panel) | ✅ done |
| Layer 12 — benchmark (`loadout benchmark`, dashboard Benchmark panel) | ✅ done |
| Layer 6 — VS Code configuration (`loadout vscode`, dashboard VS Code panel) | ✅ done (merge-fill-gaps settings; extension install needs `code`/`cursor` on PATH) |
| Layer 7 — Continue configuration (`loadout continue`, dashboard Continue panel) | ✅ done (`config.yaml` schema v1; `${env:VAR}` placeholders only) |
| Layer 8 — Agent/MCP configuration (`loadout agents`, dashboard Agents/MCP panel) | ✅ done (starter MCP + folder scaffold; filesystem MCP needs Node/npx) |
| Layer 9 — project templates (`loadout new`, dashboard Templates panel) | ✅ done (minimal runnable stubs — install deps yourself) |
| Layer 19 — offline support (`loadout offline`, dashboard offline badge) | ✅ done (graceful degrade; download cache reuse — not full repo mirroring) |
| Layer 20 — opt-in telemetry (`loadout telemetry`, dashboard Settings) | ✅ done (local-only; **no transmission**; disabled by default) |
| Continuous auto-rescan monitor | ✅ done (dashboard toggle; **default off**; min 60s interval) |
| Batch profile install wizard | ✅ done (dashboard Profiles panel; sequential install + streaming) |
| Connections page | ✅ done (presence-only env detection; setup links) |
| PATH dedupe + Loadout permission repairs | ✅ done (confirm + backup; Windows HKCU PATH write; Unix process PATH + guidance) |
| Packaging / PyPI publish | ✅ ready ([RELEASING.md](./RELEASING.md); workflow + wheel smoke in CI; **PyPI upload is manual** — configure trusted publisher + push tag) |
| Fresh-install validation | ✅ `loadout self-test` + CI e2e matrix (3 OS); manual VM runbook: [docs/e2e-validation.md](./docs/e2e-validation.md) |
| Disposable-VM mutating install sign-off | ⏳ recommended — winget/brew/apt + large model pulls ([runbook](./docs/e2e-validation.md)) |

### Known limitations (v0.1.0)

| Area | Reality |
|------|---------|
| Download manager | No throttle; offline cache reuses prior downloads only |
| Telemetry | Opt-in, local-only — no transmission |
| Benchmark inference | Needs Ollama running locally |
| Self-update | PyPI check + pip hint — no auto-upgrade |
| Templates | Minimal starter stubs |
| VS Code extensions | Requires `code` or `cursor` on PATH |
| Offline cache | Reuses downloads — not full mirror |
| PyPI | First publish needs trusted publisher + `v0.1.0` tag |

## Safety & trust

- **Official sources** — install commands use vendor package IDs (winget, choco, brew, apt,
  npm, pip, Ollama). **Trust posture:** `loadout security` and the dashboard Overview panel
  show how each component is sourced; an official URL allowlist gates direct downloads;
  the download manager (`loadout download` / dashboard) enforces the allowlist and SHA256
  when a hash is supplied. Package-manager installs delegate verification to winget/brew/etc.
- **Read-only CLI; confirm in dashboard** — `loadout scan` / `plan` / `config --show` do
  not mutate your system. Installs, repairs, model pulls, and config saves run from the
  dashboard only after you confirm (command preview + modal).
- **Three trust levels for config saves** — 🟢 SAFE (save directly), 🟡 ADVANCED (type
  `CONFIRM`), 🔴 EXPERT (type `EDIT`); each overwrite backs up to `~/.ai-loadout/backups/`.
  **Global snapshots** (`loadout backup` or dashboard) capture all Config Center files;
  restore requires typing `RESTORE`.
- **Local-first telemetry** — data stays on your machine. Telemetry is **opt-in and disabled
  by default** (Layer 20); when enabled, events are stored locally only — no transmission endpoint yet.

See [Safety, privacy & legal](#safety-privacy--legal) for policies and disclaimers.

## Safety, privacy & legal

| Document | Summary |
|----------|---------|
| [DISCLAIMER.md](./DISCLAIMER.md) | No warranty; what Loadout can change; third-party software |
| [PRIVACY.md](./PRIVACY.md) | Local-first; opt-in telemetry (local-only); what is stored under `~/.ai-loadout/` |
| [SECURITY.md](./SECURITY.md) | Vulnerability reporting; supported versions |
| [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md) | Tools Loadout automates; their licenses |
| [docs/safety-principles.md](./docs/safety-principles.md) | Design principles (local-first, confirm before risk, …) |
| [docs/confirmation-policy.md](./docs/confirmation-policy.md) | Trust levels + confirm modal behaviour |
| [docs/backup-policy.md](./docs/backup-policy.md) | Per-file config backups + global snapshots |
| [docs/logging-policy.md](./docs/logging-policy.md) | `install.log`, events, redaction |
| [docs/ai-recommendations.md](./docs/ai-recommendations.md) | Model/health advice is assistive, not guaranteed |

## Contributing

Issues and PRs are very welcome — see [CONTRIBUTING.md](./CONTRIBUTING.md) and our
[Code of Conduct](./CODE_OF_CONDUCT.md). Security reports: [SECURITY.md](./SECURITY.md).

## License

[MIT](./LICENSE). Loadout installs third-party software from their official sources; those
tools keep their own licenses — see [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md).
