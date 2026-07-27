# Build Checklist

Legend: `[x]` done · `[~]` partial/functional-but-not-complete · `[ ]` not started

## Foundation
- [x] Repo scaffolding (license, packaging, docs, hygiene)
- [x] Governance & safety docs (DISCLAIMER, PRIVACY, `docs/*` policies, README + dashboard links)
- [x] Core state engine (digital twin) + events + lifecycle
- [x] CLI entry point (`loadout` / `ai-loadout`) — version/info/scan/deps/runtimes/models/
  health/doctor/config/security/diagnostics/backup/download/update/benchmark/plan/dashboard all live (CLI stays read-only; mutations go via dashboard)
- [x] Phase 2 action engine (`ai_loadout.actions`) — build argv (win/mac/linux) + streaming
  runner (→ `install.log` + events) + single-component rescan + Layer 11 repairs + why/impact

## Layers
- [x] 1. Machine validation (OS/CPU/RAM/GPU/VRAM/disk/internet/admin/virtualization)
- [x] 2. Dependency manager (detect + decision tree)
- [x] 3. AI runtime detect (Ollama/VS Code/Continue/CLIs) + install via dashboard action engine
- [x] 4. Model recommendation (catalog + hardware-aware table + estimates)
- [x] 5. Download manager — stdlib HTTP, resume/retry, SHA256 verify, allowlist; CLI dry-run; dashboard `POST /api/download`
- [x] 6. VS Code configuration — merge-fill-gaps `settings.json`, curated extensions +
  install commands (`code`/`cursor` on PATH); CLI preview; dashboard apply + extension install
- [x] 7. Continue configuration — auto-generate `~/.continue/config.yaml` (schema v1) from
  Ollama models + env-detected providers; `${env:VAR}` only; CLI preview; dashboard apply
- [x] 8. Agent/MCP configuration — starter `.cursor/mcp.json` + rules/memory/prompts folders;
  CLI preview; dashboard apply with backup
- [x] 9. Project templates — FastAPI, Next.js, Python agent, RAG, MCP server (minimal stubs);
  `loadout new` scaffolds into empty dir; dashboard create with confirm
- [x] 10. Health check (`loadout health` — twin + live probes → actionable issues)
- [~] 11. Auto repair — start-ollama / start-docker + install/update fixes wired to the
  dashboard "Fix now" buttons; PATH-dedupe & permission repairs pending
- [x] 12. Benchmark — bounded CPU/disk/inference; tier heuristic; `benchmark-*.json` + log; CLI + dashboard panel
- [x] 13. AI doctor (`loadout doctor` — plain-language explain/fix/why/restart)
- [x] 14. Security — official URL allowlist, SHA256 helpers, trust posture report (`loadout security`, `/api/security`, dashboard Overview panel)
- [x] 15. Logging — `system.json` snapshot, redacted `diagnostics.zip` (`loadout diagnostics`, dashboard button)
- [x] 16. Update manager — PyPI self-check (offline-safe) + component upgrade report; `loadout update`; dashboard Updates panel
- [x] 17. Backup / restore — global snapshots + manifest; CLI create/list; dashboard restore with `RESTORE` gate
- [x] 18. Profiles (`loadout plan` — curated loadouts + capabilities → dry-run plan)
- [ ] 19. Offline support
- [ ] 20. Telemetry (opt-in)

## Pillars
- [x] Config Center — discover + read (redacted) + env + PATH; **dashboard editor** opens,
  edits and saves files (trust-gated + auto-backup); env panel lists **every** variable
  with full non-secret values + one-click copy
- [x] Live, **actionable** dashboard — backend (FastAPI + `/ws` + orchestrator + action
  worker) and SPA where every non-green item is fixable (install/upgrade/repair/pull/edit)
  with confirm + streaming logs + live badge updates; WS history replay fixed + HTTP
  polling fallback for action logs; **Updates** and **Benchmark** panels; direct download API
- [~] Continuous health monitoring — live event stream + per-component rescan done; periodic
  auto-rescan pending
- [~] Zero-interrupt install flow + profiles/capabilities wizard — profiles + dry-run
  planner + bootstrap scripts + per-item installs done; batch "install a whole profile"
  wizard pending
- [ ] Connections page (deferred credentials/logins)

## Quality gates
- [x] Unit tests (detection parsing, recommendation, planner, config, action engine, endpoints)
- [x] Dashboard smoke test (FastAPI TestClient + live `/ws` round-trip + action endpoints)
- [x] CI (lint + test matrix: windows/macos/linux, py3.9 + py3.12)
- [~] Manual end-to-end verification — read-only paths + dashboard actions verified live on
  Windows; winget upgrade→install fallback + PATH refresh for post-install detection added;
  a **real** winget/brew/apt install + multi-GB model pull still need a disposable-VM run
  before recommending the repo for one-click setup by others
