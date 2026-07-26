<div align="center">

# Loadout

**One command to turn any Windows, macOS, or Linux machine into a production-ready AI development workstation.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange.svg)](#project-status)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](./CONTRIBUTING.md)

</div>

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
- **Live dashboard** at `http://localhost:8421` — overall health, a GitHub-Actions-style
  install timeline, per-layer progress bars, components, models, system graphs.
- **Config Center** — every scattered config (`.continue`, `.ollama`, `.gitconfig`,
  VS Code `settings.json`, `PATH`, env vars ...) discovered, categorized, searchable,
  read-only by default, editable behind a confirmation with automatic backup.
- **Safety first** — official download sources only, checksum verification, three trust
  levels (🟢 Safe / 🟡 Advanced / 🔴 Expert), and "what changes / why / how to undo /
  restart needed" before any risky edit.
- **Profiles & Capabilities** — pick *AI Developer* or *Agent Developer* instead of
  ticking 50 tools; each expands transparently into the underlying components.

## Quick start

> ⚠️ **Alpha.** Read [Project status](#project-status) for exactly what is implemented
> today. Nothing mutating runs without your confirmation, and `--dry-run` shows the full
> plan without changing anything.

```bash
# 1. Get the code
git clone https://github.com/bnvukin/ai-loadout.git
cd ai-loadout

# 2. Install (Python 3.9+)
pip install -e ".[dashboard]"

# 3. Scan your machine (read-only) and see what Loadout would do
loadout scan
loadout plan --profile ai-developer --dry-run

# 4. Open the live dashboard
loadout dashboard
```

One-command bootstrap scripts (`bootstrap.ps1` / `bootstrap.sh`) that install Python for
you and launch the wizard are part of the roadmap below.

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
- `ai_loadout.detect` — Layers 1 & 2 (machine + dependency detection).
- `ai_loadout.models` — Layer 4 (catalog + hardware-aware recommendation).
- `ai_loadout.dashboard` — FastAPI + WebSocket live UI at `:8421`.
- ... (more modules added per layer)

## Project status

Loadout is in **active alpha**. This table is kept honest — it reflects what actually
works, not the vision.

| Area | Status |
|------|--------|
| Repo scaffolding, packaging, license | 🚧 in progress |
| Core state engine (digital twin) | ⏳ planned next |
| Layer 1 — machine detection | ⏳ |
| Layer 4 — model recommendation | ⏳ |
| Live dashboard | ⏳ |
| Everything else | ⏳ roadmap |

## Safety & trust

- Downloads only from **official sources**; installers are checksum-verified where a
  published hash exists.
- **Read-only by default.** Mutating actions require explicit confirmation; risky ones
  require typing `EDIT`.
- Loadout never transmits your data. Telemetry (if ever added) is strictly opt-in and
  anonymous.

## Contributing

Issues and PRs are very welcome — see [CONTRIBUTING.md](./CONTRIBUTING.md) and our
[Code of Conduct](./CODE_OF_CONDUCT.md). Security reports: [SECURITY.md](./SECURITY.md).

## License

[MIT](./LICENSE). Loadout installs third-party software from their official sources; those
tools keep their own licenses — see [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md).
