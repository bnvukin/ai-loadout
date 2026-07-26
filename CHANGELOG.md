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
- Test suite (17 tests) covering events, lifecycle, state persistence, and the CLI; ruff
  lint/format configured and passing.
