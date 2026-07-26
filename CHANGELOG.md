# Changelog

All notable changes to Loadout are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
