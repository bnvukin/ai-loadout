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
- Cleanup: rewrote history so every commit is authored/committed by **bnvukin only** (no
  `cursoragent` co-author). Added a repo-local `commit-msg` hook that strips any
  `Co-authored-by: Cursor` trailer from future commits; force-pushed the clean history.

### Session 2 — 2026-07-26 (Phase 2: make it act)
User feedback on the live dashboard drove this phase: (SS1) anything not green must be
resolvable in-dashboard with steps/impact; (SS2) one-click model install + local status;
(SS3) Config Center must be editable and show *all* env vars.
- Batch 14: **action engine** (`ai_loadout.actions`). `commands.py` builds exact argv for
  install/upgrade (winget/choco/brew/apt/npm/pip; wraps Windows `.cmd`/`.bat` for
  `shell=False`) and `ollama pull`; `runner.py` streams stdout → EventBus + `install.log`,
  flips the component busy → re-detects it (green on success / FAILED+RED on error);
  `repair.py` = Layer 11 (start-ollama/start-docker + install/update delegation);
  `advice.py` = per-component impact / what-it-unlocks / docs link. 20 hermetic tests.
- Batch 15: **actionable APIs** on the dashboard — `/api/component/{key}/{install,upgrade,
  rescan}`, `/api/component/{key}/advice`, `/api/models/{key}/pull`, `/api/models/refresh`,
  `/api/repair`, `GET /api/config/{key}?raw=1` + `POST /api/config/{key}` (save,
  trust-gated + backup), and `GET /api/env` (every var, redacted). Orchestrator gained a
  single-flight background action worker so installs don't block scans. 16 new tests.
- Batch 16: **actionable SPA** — Components get Install/Update/Retry + "Why?" + re-detect
  with a confirm modal (exact command + UAC/sudo warning) and a streaming action-log;
  Overview issues get inline "Fix now"; Models install with one click + "installed" tag +
  Refresh; Config Center opens an editor and saves (SAFE direct, ADVANCED/EXPERT gated) and
  the env panel toggles AI-relevant/All with search. Vanilla JS modal/toast/spinner, no
  build step. `node --check` clean.
- Batch 17: docs — CHANGELOG/README/CHECKLIST/PROJECT-MEMORY updated for Phase 2.

## Delivery snapshot (session 2)
122 tests green locally; the dashboard was verified live end-to-end on Windows: advice,
dry-run install (no execution), per-component rescan (git → green), model refresh, repair
preview (`ollama serve`), config raw-read, and all **71** environment variables surfaced.
The dashboard can now *act* (with confirm + logs); the CLI stays read-only.

**Still needed before recommending the repo for one-click setup by others:** a real
mutating install (winget/brew/apt) + a multi-GB `ollama pull` run in a disposable VM on
each OS, a PyPI publish (so `pip install ai-loadout` works without cloning), and a
"install a whole profile" batch flow. Remaining layers: 5-9, 12, 14-17, 19-20.

### Session 3 — 2026-07-26 (dashboard reliability + env UX)
User reported the action-log modal stuck on "Starting..." (WS showed "reconnecting...") and
env var values appearing trimmed with no easy copy.
- **Root cause:** `/ws` replayed 50+ buffered events in a tight `send_json` loop, which
  dropped the connection at message 0 (`ConnectionClosedError: no close frame received or
  sent`) before live events could arrive. Installs worked server-side; only the UI stream
  was broken.
- **Fix:** yield with `await asyncio.sleep(0)` between history frames, wrap sends in a
  safe helper, serialize history via `to_dict()`. Frontend action logs now also poll
  `GET /api/events?after=<id>` every ~1.2s (deduped by event id) so progress survives a
  flaky socket during multi-minute installs.
- **Env UX:** removed CSS ellipsis truncation on value cells; added one-click copy on env
  vars, config paths, and PATH entries (secrets remain masked). Backend already returned
  full values — display was the issue.
- Verified: 124 tests green; live `/ws` holds open with non-empty history; dry-run install
  API confirmed.
- **Follow-up:** Real VM end-to-end install still pending.

### Session 4 — 2026-07-26 (CI py3.9 + winget recovery + PATH refresh)
- **CI py3.9 root cause (from GitHub logs):** Pydantic failed evaluating FastAPI route
  annotations ``dict | None`` at runtime (`TypeError: Unable to evaluate type annotation
  'dict | None'`). All 16 dashboard tests failed on 3.9 across win/mac/linux; 3.12 passed.
  Fix: ``Optional[dict]`` on POST route payloads in `server.py`; ruff UP045 ignored there.
- **winget actions:** upgrade→install fallback when "No installed package found matching
  input criteria"; non-zero exits with "already installed / no available upgrade" treated
  as success (`actions/winget.py`, `runner._execute_with_recovery`).
- **Windows PATH refresh:** `util/path_env.refresh_process_path()` reads HKCU/HKLM Path
  before detection so pnpm/uv show green after winget install without dashboard restart.
- 133 tests green locally after changes.

### Session 5 — 2026-07-26 (PATH refresh hardening + copy everywhere)
- **pnpm/uv still grey (true root cause):** winget installs to fully-expanded dirs under
  ``HKCU\\Environment\\Path`` (e.g. ``...\\WinGet\\Packages\\pnpm.pnpm_...``). A long-running
  dashboard keeps a *stale* process PATH (often with unexpanded ``%USERPROFILE%\\WindowsApps``
  only). ``shutil.which`` does not expand ``%VAR%`` inside PATH entries, so the first fix
  (append registry to stale PATH) was insufficient when merge order/expansion was wrong.
  Standalone python verification was misleading — fresh processes inherit an updated PATH.
- **Fix:** rebuild PATH registry-first with per-entry ``expandvars``; call refresh in
  ``detect_all``, ``detect_one``, ``rescan_component``, and ``proc.which`` (plus ``where.exe``
  fallback). Verified against a live server started with a deliberately stale PATH: HTTP
  rescan + full scan return pnpm/uv green.
- **Copy UX:** command previews (install/update/pull), Why? panel, action log, config paths,
  doc links — all reuse the env-var copy button + toast pattern.
- 137 tests green locally.

### Session 6 — 2026-07-27 (governance & safety docs)
- Added honest governance pack: `DISCLAIMER.md`, `PRIVACY.md`, `docs/confirmation-policy.md`,
  `docs/backup-policy.md`, `docs/logging-policy.md`, `docs/ai-recommendations.md`,
  `docs/safety-principles.md`.
- Enhanced `SECURITY.md` (supported versions, private reporting, no secrets in public issues),
  `THIRD_PARTY_NOTICES.md` (tool table + URLs), `CONTRIBUTING.md` (contribution safety).
- README: new "Safety, privacy & legal" section; softened checksum/overclaim in Highlights
  and Safety & trust (Layer 14 planned, not done).
- Dashboard sidebar: unobtrusive disclaimer + links to Disclaimer, Privacy, Safety on GitHub.

### Session 7 — 2026-07-27 (Wave A: Layers 14, 15, 17)
- **Layer 14:** `ai_loadout.security` — URL allowlist, SHA256 verify/compute, trust posture
  from deps/runtimes registries; `loadout security`, `GET /api/security`, Overview panel.
- **Layer 15:** `system.json` writer, `diagnostics.zip` bundler with redaction;
  `loadout diagnostics`, `POST /api/diagnostics`, Config Center diagnostics download UI.
- **Layer 17:** global config snapshots + manifest; `loadout backup`/`restore`; dashboard
  Backups panel with `RESTORE` confirmation gate (EXPERT).
- 151 tests green locally; README/CHECKLIST/CHANGELOG/governance docs updated honestly
  (Layer 5 download-manager will wire checksum checks; no env-var restore yet).

### Session 8 — 2026-07-27 (Wave B: Layers 5, 16, 12)
- **Layer 5:** `ai_loadout.download` — resume/retry/allowlist/SHA256; `loadout download`
  dry-run; dashboard confirmed download with streaming logs.
- **Layer 16:** PyPI self-check + component upgrade report; `loadout update`;
  dashboard Updates panel with existing upgrade actions + rollback hints.
- **Layer 12:** bounded CPU/disk/Ollama inference benchmark; tier heuristic;
  `loadout benchmark`; dashboard Benchmark panel.
- 170 tests green locally. Honest partials: inference only when Ollama responds;
  self-update is check + pip hints (no auto-upgrade); model pulls still use Ollama CLI.
- **CI fix (`b42a5bd`):** `ProgressFn` alias used `int | None` inside `Callable[...]` —
  evaluated at import on py3.9; switched to `Optional[int]`. CI run `30279061333` all green.

### Session 9 — 2026-07-27 (Wave C: Layers 6, 7, 8, 9)
- **Layer 6:** `ai_loadout.vscode` — merge-fill-gaps recommended settings, curated extensions,
  `preview()`/`apply()` with backup; CLI `loadout vscode`; dashboard VS Code panel + extension
  install via action engine.
- **Layer 7:** `ai_loadout.continue_cfg` — `config.yaml` schema **v1**; Ollama models from twin
  + cloud providers when env vars present; secrets as `${env:VAR}` only; CLI + dashboard.
- **Layer 8:** `ai_loadout.agents` — starter MCP config + folder scaffold; CLI + dashboard.
- **Layer 9:** `ai_loadout.templates` — five minimal inline scaffolds; `loadout new`; dashboard
  Templates panel; refuses non-empty target without force.
- Shared utilities: `config/merge.py`, `config/write_util.py`, `util/yaml_simple.py`.
- 188 tests green locally. Honest partials: templates are minimal stubs; extension install needs
  `code`/`cursor` on PATH; Continue uses lightweight YAML writer (not full YAML spec); MCP
  filesystem server needs Node/npx.

## Open questions / future

- Real end-to-end install test in a disposable VM/sandbox per OS before recommending
  mutating runs to strangers.
- PyPI release + versioned tag so bootstrap can `pip install ai-loadout` (no git clone).
- Batch profile install (run the whole `loadout plan` from the dashboard with live progress).
- Elevation UX on Windows (some winget installs prompt UAC / need an elevated shell).
