# Build Checklist

Legend: `[x]` done · `[~]` partial/functional-but-not-complete · `[ ]` not started

## Foundation
- [~] Repo scaffolding (license, packaging, docs, hygiene)
- [ ] Core state engine (digital twin) + events + lifecycle
- [ ] CLI entry point (`loadout` / `ai-loadout`)

## Layers
- [ ] 1. Machine validation (OS/CPU/RAM/GPU/VRAM/disk/internet/admin/virtualization)
- [ ] 2. Dependency manager (detect + decision tree)
- [ ] 3. AI runtime install (Ollama, Open WebUI, Continue, CLIs)
- [ ] 4. Model recommendation (catalog + hardware-aware table + estimates)
- [ ] 5. Download manager (resume/retry/verify)
- [ ] 6. VS Code configuration (extensions + settings)
- [ ] 7. Continue configuration (auto-generate)
- [ ] 8. Agent/MCP configuration
- [ ] 9. Project templates
- [ ] 10. Health check
- [ ] 11. Auto repair
- [ ] 12. Benchmark
- [ ] 13. AI doctor
- [ ] 14. Security (checksums, official URLs)
- [ ] 15. Logging (install/benchmark logs, diagnostics.zip)
- [ ] 16. Update manager
- [ ] 17. Backup / restore
- [ ] 18. Profiles
- [ ] 19. Offline support
- [ ] 20. Telemetry (opt-in)

## Pillars
- [ ] Config Center (configs + env vars + PATH, read-only/edit w/ confirm + backup)
- [ ] Live dashboard (health, install timeline, live install, components, models, system)
- [ ] Continuous health monitoring
- [ ] Zero-interrupt install flow + profiles/capabilities wizard
- [ ] Connections page (deferred credentials/logins)

## Quality gates
- [ ] Unit tests (detection parsing via fixtures, recommendation, planner, config discovery)
- [ ] Dashboard smoke test (FastAPI TestClient)
- [ ] CI (lint + test matrix: windows/macos/linux)
- [ ] Manual end-to-end test notes / sandbox verification
