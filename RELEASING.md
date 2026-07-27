# Releasing Loadout

Loadout uses [Semantic Versioning](https://semver.org/). The single source of truth for the
version string is `src/ai_loadout/__init__.py` (`__version__`); Hatch reads it dynamically
via `[tool.hatch.version]` in `pyproject.toml`.

## One-time PyPI setup (maintainer)

1. **Create the PyPI project** at [pypi.org](https://pypi.org/) (name: `ai-loadout`).
2. **Configure trusted publishing (OIDC)** on PyPI:
   - Owner: `bnvukin`
   - Repository: `ai-loadout`
   - Workflow: `release.yml`
   - Environment: `pypi` (for production releases)
3. **Optional — TestPyPI dry run:** create a project on [test.pypi.org](https://test.pypi.org/)
   and add a trusted publisher with environment name `testpypi` (same repo/workflow).
4. **GitHub environments:** In the repo settings → Environments, create `pypi` and
   `testpypi` (no secrets required — OIDC only).

No API tokens are stored in this repository.

## Local build + verify (before tagging)

```powershell
# From repo root (PowerShell)
python -m pip install --upgrade pip build twine
python -m build
twine check dist/*

# Clean venv smoke test
python -m venv .wheel-smoke
.\.wheel-smoke\Scripts\pip install dist\ai_loadout-*.whl[dashboard]
.\.wheel-smoke\Scripts\loadout --help
.\.wheel-smoke\Scripts\loadout version
.\.wheel-smoke\Scripts\python -c "from ai_loadout.dashboard.assets import static_dir; print(static_dir())"
```

```bash
# macOS / Linux equivalent
python -m pip install --upgrade pip build twine
python -m build
twine check dist/*
python -m venv .wheel-smoke
.wheel-smoke/bin/pip install dist/ai_loadout-*.whl[dashboard]
.wheel-smoke/bin/loadout --help
.wheel-smoke/bin/loadout version
```

Expected: `loadout --help` lists all subcommands; `loadout version` prints `Loadout 0.1.0`;
`static_dir()` resolves to a directory containing `index.html`, `app.js`, and `style.css`.

CI runs the same wheel smoke test on every push (`.github/workflows/ci.yml` → **Package** job).

## Publish to TestPyPI (manual dry run)

1. GitHub → **Actions** → **Release** → **Run workflow**
2. Choose target: **testpypi**
3. After success, install from TestPyPI:

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ ai-loadout[dashboard]
```

## Publish to PyPI (production)

1. Update `CHANGELOG.md` and bump `__version__` if needed.
2. Commit and push to `main`.
3. Create and push an annotated tag:

```bash
git tag -a v0.1.0 -m "Loadout 0.1.0"
git push origin v0.1.0
```

4. The **Release** workflow builds sdist + wheel, runs `twine check`, and publishes via OIDC.
5. Verify:

```bash
pip install ai-loadout[dashboard]
loadout dashboard
```

## What ships in the wheel

- Python package `ai_loadout` (all layers)
- Dashboard SPA: `ai_loadout/dashboard/static/` (`index.html`, `app.js`, `style.css`) — included
  automatically by hatchling as part of the package tree (no separate `package-data` needed)
- Console scripts: `loadout` and `ai-loadout` → `ai_loadout.cli:main`
- Templates are inline Python strings (no extra package data needed)

Runtime dependencies: `psutil` (core). Install the dashboard with `pip install ai-loadout[dashboard]`
which adds `fastapi` and `uvicorn[standard]`.
