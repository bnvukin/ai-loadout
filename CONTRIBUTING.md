# Contributing to Loadout

Thanks for helping build the AI workstation control center. Contributions of every
size are welcome — bug reports, docs, a new model in the catalog, or a whole new layer.

## Ground rules

- **Be kind.** See the [Code of Conduct](./CODE_OF_CONDUCT.md).
- **Safety first.** Anything that mutates a user's machine must be reversible, logged,
  and gated behind explicit confirmation. Never download from unofficial mirrors.
- **The state engine is the source of truth.** Actions update the digital-twin state
  first; the UI reads from it. Don't bypass it.
- **Honest status.** If something is a stub, mark it as a stub. The README status table
  must stay accurate.

## Dev setup

```bash
git clone https://github.com/bnvukin/ai-loadout.git
cd ai-loadout
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Unix:     source .venv/bin/activate
pip install -e ".[dev]"
```

## Before you open a PR

```bash
ruff check .
ruff format --check .
pytest
```

- Add or update tests for any behavior change.
- Detection/parsing code should be tested against captured sample output (see
  `tests/fixtures/`) so it does not depend on the machine running the tests.
- Keep runtime dependencies minimal — the core install must stay lightweight and
  auditable. Heavier deps go behind an optional extra in `pyproject.toml`.

## Adding a model to the catalog

Model metadata lives in `src/ai_loadout/models/catalog.py` (and/or a bundled JSON).
Include: parameter size, quantized on-disk size, RAM/VRAM needed, coding/reasoning/speed
ratings, offline flag, provider, and a one-line "best for". A test validates the schema.

## Commit style

Small, focused commits with clear messages. Conventional prefixes are appreciated
(`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`) but not required.
