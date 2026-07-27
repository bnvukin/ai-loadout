# Changelog

All notable changes to Loadout are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Wave F — fresh-install validation:** `loadout self-test` (and `loadout doctor --self-test`)
  read-only install confidence checks; CI e2e matrix (win/mac/linux clean venv + `--bind-http`);
  [docs/e2e-validation.md](./docs/e2e-validation.md) manual VM runbook; README Known limitations.

## [0.1.0] - 2026-07-27

First pip-installable alpha release. All 20 layers + product pillars implemented.

### Added
- **Packaging:** hatchling build; dashboard SPA ships as part of the package tree;
  console scripts `loadout` / `ai-loadout`; version `0.1.0` from `__init__.__version__`.
- **CI:** wheel smoke job (build → `twine check` → install wheel → CLI + static asset verify).
- **Release:** `.github/workflows/release.yml` — OIDC trusted publishing to PyPI / TestPyPI.
- **Docs:** [RELEASING.md](./RELEASING.md), README Install + Quickstart sections.

### Notes (honest partials at 0.1.0)
- Download throttle deferred; offline cache reuses prior downloads only (not full mirroring).
- Telemetry is opt-in, local-only — **no transmission endpoint**.
- Inference benchmark needs a running Ollama; self-update is check + pip hint only.
- Project templates are minimal starter stubs; extension install needs `code`/`cursor` on PATH.

## [Unreleased — historical]

### Added
- Project scaffolding: MIT license, packaging (`pyproject.toml`), contributor docs,
  security policy, third-party notices, `.gitignore`/`.editorconfig`.
- Core state engine (the "digital twin"): thread-safe `StateStore` with atomic JSON
  persistence, a shared component lifecycle (`Detected → ... → Healthy`), traffic-light
  health aggregation, and a bounded pub/sub `EventBus` for live updates.
- CLI entry point (`loadout` / `ai-loadout`) with `version` and `info` commands and a
  discoverable list of upcoming subcommands.
- Test suite covering events, lifecycle, state persistence, and the CLI; ruff
  lint/format configured and passing.
- Layer 1 (machine validation): cross-platform detection of OS, CPU, RAM, GPU/VRAM
  (nvidia-smi / pynvml / OS fallbacks), disk, internet, admin rights and virtualization.
  Pure output parsers are unit-tested against captured fixtures; `loadout scan` writes the
  result into the digital twin and renders health cards.
- Safe subprocess helper (`util.proc`) used by detection/health probes.
- Layer 4 (model recommendation): a curated model catalog (schema-validated) plus a
  hardware-aware engine that estimates tokens/sec, memory, load time and context per
  model, ranks the catalog for the detected machine (fits / tight / too_big), assigns
  "Best Overall / Fastest / Best Coding" labels, and explains the top pick. `loadout
  models` renders the comparison table.
- Layer 2 (dependency manager): version-tolerant detection of Git/Python/Node/npm/pnpm/
  uv/Docker/PowerShell/WSL/winget/Chocolatey/Homebrew/CUDA/VS Build Tools with a
  skip/upgrade/install decision per tool, package-manager awareness (winget/choco/brew/
  apt/...), and injectable probes for hermetic testing. `loadout scan` now also reports the
  toolchain; `loadout deps` gives a focused view.
- Layer 3 (AI runtimes, detection): detects Ollama (+ local models via `ollama list`),
  VS Code (+ version), Continue, Cursor, Open WebUI, LM Studio, AnythingLLM and the agent
  CLIs (Claude Code, Codex, Gemini, OpenCode) via CLI/port/config-dir signals. `loadout
  scan` now reports runtimes; `loadout runtimes` gives a focused view and lists local
  models. (Install actions land with the orchestrator.)
- Layers 10 & 13 (health check + AI doctor): `loadout health` inspects the twin plus live
  probes (Ollama server, Docker daemon, disk, internet, GPU, out-of-date/missing tools)
  and lists actionable issues; `loadout doctor` explains each in plain language with a
  fix, why-it-matters, and restart scope. Explanations are data-driven and testable.
- Config Center (`loadout config`): discovers well-known config files (Continue, VS Code,
  Cursor, Git, Docker, npm, pip, Hugging Face token, shell profiles) across OSes, inspects
  AI-relevant environment variables, and analyses `PATH` for missing/duplicate entries.
  Everything is **read-only** and secrets are redacted before display; `--show <key>`,
  `--env` and `--path` focus the view. Trust-gated, backup-first edits are implemented in
  `config.edit` (used by the dashboard later; not yet exposed on the CLI).
- Live dashboard backend (`loadout dashboard`): a FastAPI app over the digital twin with
  read APIs (`/api/state`, `/api/health`, `/api/hardware`, `/api/components`, `/api/models`,
  `/api/config`), a scan trigger (`POST /api/scan`, `/api/tasks/{name}`), and a `/ws`
  WebSocket that streams `EventBus` events live. A background `Orchestrator` runs the
  detection layers off the request thread and reports per-task status. The web stack is an
  optional extra (`pip install ai-loadout[dashboard]`).
- Live dashboard UI: a dependency-free, no-build vanilla-JS SPA (dark theme) served from
  the backend, with Overview (health ring + machine + issues), Components, Models, Config
  Center (with a redacted file viewer), and a live Activity stream. A "Rescan" button
  triggers the orchestrator and per-task progress chips update in real time over `/ws`.
- Layer 18 profiles + install planner (`loadout plan`): curated "loadouts" (minimal,
  student, web-ai-dev, agentic-coder, ai-research, ml-engineer) plus add-on capabilities
  (containers, gpu, web-ui, coding-agents). `build_plan` reconciles a profile against the
  digital twin and emits an ordered, **dry-run** plan (install/upgrade/pull/skip/manual)
  with the exact package-manager command per step and a hardware-aware model pick.
- Bootstrap scripts (`bootstrap.ps1`, `bootstrap.sh`): the "one command" from a bare
  machine — ensure Python (winget/Homebrew/apt), install Loadout, run the first scan.
  Official sources only, every action printed, `-DryRun`/`--dry-run` preview.
- Continuous integration: GitHub Actions workflow running `ruff check` + `ruff format
  --check` and the pytest suite across Windows/macOS/Linux on Python 3.9 and 3.12, plus a
  CLI smoke test (`version`/`scan`/`plan`).
- Docs: README "Commands available today" reference table and accurate profile names; the
  build checklist reflects the shipped CLI surface.
- **Phase 2 — action engine (`ai_loadout.actions`):** turns the read-only advisor into
  something that can act. Builds the exact argv for install/upgrade
  (winget/choco/brew/apt/npm/pip, with Windows `.cmd`/`.bat` wrapping) and model pulls;
  a streaming runner executes it, tees stdout to the `EventBus` **and** `install.log`,
  flips the component to a busy lifecycle state, then re-detects it so its badge reflects
  reality (green on success, FAILED/RED with the error tail on failure). Layer 11 repairs
  (`start-ollama`, `start-docker`, plus install/update delegation) and a per-component
  "why / impact / docs link" advisor round it out. Everything defaults to explicit, logged
  runs; a dry run returns the command that *would* execute.
- **Phase 2 — actionable dashboard APIs:** `POST /api/component/{key}/{install,upgrade}`
  (background, streamed), `/rescan` (re-detect one component), `GET
  /api/component/{key}/advice`, `POST /api/models/{key}/pull` + `/api/models/refresh`,
  `POST /api/repair`, `GET /api/config/{key}?raw=1` and `POST /api/config/{key}` (save,
  trust-gated + backup), and `GET /api/env` (now lists **every** environment variable,
  secrets masked). The orchestrator gained a single-flight background action worker.
- **Phase 2 — actionable dashboard UI:** every non-green item is now resolvable in the
  browser. Components show Install/Update/Retry + "Why?" + re-detect, with a confirm modal
  (exact command, UAC/sudo warning) and a live action-log; Overview issues get inline
  "Fix now" buttons. Models install with one click (live pull log) and show an "installed"
  tag + Refresh for local status. The Config Center opens files in an editor and saves
  them (SAFE directly; ADVANCED/EXPERT require typing CONFIRM/EDIT; automatic backup), and
  the environment panel toggles AI-relevant / All with search. Adds a modal/toast/spinner
  system — still vanilla JS, no build step.

### Fixed
- **WebSocket history replay:** rapid-fire `/ws` backlog delivery no longer drops the
  connection on connect (yield between sends + resilient send wrapper + `to_dict()` replay).
  Action-log modal also polls `/api/events` as a fallback when the socket is flaky.
- **Config Center env display:** non-secret values are no longer CSS-truncated; one-click
  copy buttons on env vars, config paths, and PATH entries (secrets stay masked).

### Fixed (session 3)
- **Python 3.9 CI:** FastAPI route bodies used ``dict | None`` annotations that Pydantic
  cannot evaluate on 3.9 — switched to ``Optional[dict]`` on dashboard POST handlers.
- **winget upgrade/install recovery:** upgrade falls back to install when winget reports
  no installed package; "already installed / no upgrade available" exits count as success.
- **Stale PATH on Windows:** dependency/runtime detection refreshes PATH from the registry
  so tools installed while the dashboard is running (pnpm, uv, …) rescan green without restart.
- **PATH refresh hardened:** registry-first rebuild with per-entry ``%VAR%`` expansion;
  ``proc.which`` refreshes before lookup and falls back to ``where.exe`` on Windows.
- **Copy buttons:** install/update confirm modals, Why? advice (commands + doc links), model
  pull preview, action-log modal, and config editor paths all have one-click copy + toast.

### Added
- **Layer 5 — Download manager:** `ai_loadout.download` with stdlib HTTP streaming,
  resume (`Range`), retry/backoff, official-source allowlist, and SHA256 verification.
  Read-only `loadout download`; dashboard `GET /api/download/plan` and confirmed
  `POST /api/download` with event-bus progress.
- **Layer 16 — Update manager:** PyPI self-update check with offline fallback;
  component upgrade report from the digital twin; read-only `loadout update`;
  `GET /api/updates` and dashboard Updates panel with upgrade buttons + rollback hints.
- **Layer 12 — Benchmark:** bounded CPU/disk/inference micro-benchmark; tier heuristic;
  `benchmark-*.json` + `benchmark.log`; `loadout benchmark` and dashboard Benchmark panel
  (`POST /api/benchmark`, `GET /api/benchmark/latest`).

### Added
- **Wave D — Layers 19–20 + pillars:**
  - **Layer 19 — Offline:** `ai_loadout.offline` connectivity probe (timeout-guarded, injectable),
    offline gating for network actions, `~/.ai-loadout/cache/` for download reuse; `loadout offline`;
    dashboard online/offline badge + `GET /api/connectivity`.
  - **Layer 20 — Telemetry:** opt-in only (`telemetry_enabled: false` default in `config.json`);
    whitelisted anonymous fields stored locally in `~/.ai-loadout/telemetry/`; **no transmission**;
    `loadout telemetry --status`; dashboard Settings/Privacy panel.
  - **Pillar — Continuous monitor:** optional orchestrator periodic rescan (**default off**,
    min 60s); `GET/POST /api/monitor`.
  - **Pillar — Profile install wizard:** `GET /api/profiles`, plan + confirmed sequential install;
    dashboard Profiles panel.
  - **Pillar — Connections:** `GET /api/connections` — present/absent env vars only.
  - **Pillar — PATH repairs:** `path-dedupe` and `fix-loadout-perms` repair actions with backup.

### Added
  - **Layer 6 — VS Code:** `ai_loadout.vscode` with merge-fill-gaps `settings.json`,
    curated extension list + `code --install-extension` command builder (action engine, not
    `shell=True`); read-only `loadout vscode`; dashboard VS Code panel (preview, apply with
    backup, per-extension install). Extension install requires `code` or `cursor` on PATH.
  - **Layer 7 — Continue:** `ai_loadout.continue_cfg` builds `~/.continue/config.yaml`
    (schema **v1**, YAML via lightweight `yaml_simple` — no PyYAML dep) from detected Ollama
    models and env-present cloud providers; API keys as `${env:OPENAI_API_KEY}` placeholders
    only; read-only `loadout continue`; dashboard Continue panel.
  - **Layer 8 — Agents/MCP:** `ai_loadout.agents` starter `.cursor/mcp.json` (filesystem MCP
    via npx) + `.cursor/rules`, `.cursor/memory`, `prompts/`, `memory/` scaffold; read-only
    `loadout agents`; dashboard Agents/MCP panel.
  - **Layer 9 — Templates:** `ai_loadout.templates` with five inline scaffolds (FastAPI,
    Next.js, Python agent, RAG, MCP server) — minimal starter files, not full dependency
    trees; `loadout new <template> <name>` (CLI may create new dirs; refuses non-empty without
    `--force`); dashboard Templates panel.
  - Shared: `config/merge.py` (JSONC + merge-fill-gaps), `config/write_util.py` (atomic write +
    backup), `util/yaml_simple.py`.

### Added `ai_loadout.security` with official URL allowlist
  (`is_official_source`), streaming SHA256 helpers (`compute_sha256`, `verify_sha256`),
  known-hash table scaffold for direct downloads, and a per-component trust posture report.
  Read-only `loadout security`, `GET /api/security`, and an Overview panel in the dashboard.
- **Layer 15 — Logging & diagnostics:** `system.json` machine snapshot under
  `~/.ai-loadout/logs/` (secrets redacted); `loadout diagnostics` and `POST /api/diagnostics`
  bundle logs + state + versions into a timestamped, redacted zip; dashboard "Download
  diagnostics" button with file download endpoint.
- **Layer 17 — Global backup / restore:** `ai_loadout.backup` snapshots Config Center files
  + PATH/env manifest under `~/.ai-loadout/backups/<ts>/`; `loadout backup` / `--list`;
  `loadout restore <id> --confirm RESTORE`; dashboard Backups panel with create + typed
  restore gate (`RESTORE`).

### Added
- **Governance & safety docs:** `DISCLAIMER.md`, `PRIVACY.md`, and `docs/` policies
  (confirmation, backup, logging, AI recommendations, safety principles); enhanced
  `SECURITY.md`, `THIRD_PARTY_NOTICES.md`, `CONTRIBUTING.md`; README honesty fixes for
  Layer 14 checksum claims; dashboard sidebar safety footer with doc links.
