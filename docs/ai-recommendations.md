# AI recommendations disclaimer

Loadout provides **assistive** guidance. It is not a substitute for your own judgment.

## What Loadout recommends

- **Model catalog & hardware fit** (`loadout models`) — estimates tokens/sec, RAM, and
  "fits / tight / too_big" from detected hardware. Estimates use heuristics and a curated
  catalog; real performance varies by workload, quantization, and drivers.
- **Health check & AI doctor** (`loadout health`, `loadout doctor`) — surfaces issues and
  plain-language explanations from the digital twin + live probes.
- **Install plans** (`loadout plan --profile …`) — dry-run list of suggested install/skip
  steps; **does not execute** without dashboard confirmation.
- **Repair hints** — e.g. start Ollama/Docker; delegate install/update to the action engine
  when you confirm.

## What is NOT guaranteed

- Recommended models will run flawlessly on your GPU/CPU.
- Health issues lists are complete (optional components may stay gray).
- Repair actions fix every root cause (Layer 11 is **partial** — PATH dedupe, permission
  fixes, etc. are still on the roadmap).
- Benchmark numbers (**Layer 12 — planned**) — not available today.

## Your responsibility

- Validate model licenses and usage terms before pulling weights.
- Test changes on non-production systems when possible.
- Read command previews before confirming installs.

See [DISCLAIMER.md](../DISCLAIMER.md) and [safety-principles.md](./safety-principles.md).
