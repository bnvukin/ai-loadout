import pytest

from ai_loadout.core.lifecycle import Category, ComponentState
from ai_loadout.core.models import Component, Hardware, ModelEntry
from ai_loadout.core.state import StateStore
from ai_loadout.plan import planner
from ai_loadout.profiles.registry import PROFILES, by_key, profile_keys


@pytest.fixture
def win_managers(monkeypatch):
    # Deterministic package-manager environment so command strings are stable.
    monkeypatch.setattr(planner, "available_managers", lambda *a, **k: ["winget"])
    monkeypatch.setattr(planner, "preferred_manager", lambda *a, **k: "winget")


def _store(components=()):
    store = StateStore(autosave=False)
    store.set_hardware(Hardware(os_family="windows", ram_total_gb=16.0))
    for c in components:
        store.upsert_component(c)
    return store


# -- profiles registry ------------------------------------------------------------------
def test_profiles_have_unique_keys_and_known_refs():
    from ai_loadout.deps.registry import by_key as dep_by_key
    from ai_loadout.models.catalog import by_key as model_by_key
    from ai_loadout.runtimes.registry import by_key as rt_by_key

    assert len(profile_keys()) == len(set(profile_keys()))
    for p in PROFILES:
        for d in p.deps:
            assert dep_by_key(d), f"{p.key}: unknown dep {d}"
        for r in p.runtimes:
            assert rt_by_key(r), f"{p.key}: unknown runtime {r}"
        for m in p.models:
            assert model_by_key(m), f"{p.key}: unknown model {m}"


# -- planning ---------------------------------------------------------------------------
def test_missing_dep_becomes_install_with_command(win_managers):
    store = _store()
    plan = planner.build_plan(store, "minimal", include_models=False)
    git = next(s for s in plan.steps if s.key == "git")
    assert git.action == "install"
    assert git.command == "winget install --id Git.Git -e --source winget"


def test_present_dep_is_skipped(win_managers):
    store = _store(components=[Component(key="git", name="Git", state=ComponentState.INSTALLED)])
    plan = planner.build_plan(store, "minimal", include_models=False)
    git = next(s for s in plan.steps if s.key == "git")
    assert git.action == "skip"
    assert git.command is None


def test_runtime_without_package_id_is_manual(win_managers):
    store = _store()
    plan = planner.build_plan(store, "minimal", include_models=False)
    cont = next(s for s in plan.steps if s.key == "continue")
    assert cont.action == "manual"  # Continue has no winget/npm/pip id
    ollama = next(s for s in plan.steps if s.key == "ollama")
    assert ollama.action == "install" and ollama.command.startswith("winget install")


def test_model_step_pulls_best_fit(win_managers):
    store = _store()
    plan = planner.build_plan(store, "minimal", include_models=True)
    models = [s for s in plan.steps if s.kind == "model"]
    assert len(models) == 1
    assert models[0].action == "pull"
    assert models[0].command.startswith("ollama pull ")


def test_downloaded_model_is_skipped(win_managers):
    store = _store()
    store.upsert_model(ModelEntry(name="llama3.2:3b", downloaded=True))
    plan = planner.build_plan(store, "minimal", include_models=True)
    model = next(s for s in plan.steps if s.kind == "model")
    assert model.action == "skip"


def test_capabilities_inject_requirements(win_managers):
    store = _store()
    plan = planner.build_plan(store, None, ["containers"], include_models=False)
    assert plan.profile is None
    assert any(s.key == "docker" for s in plan.steps)


def test_summary_counts(win_managers):
    store = _store(
        components=[Component(key="python", name="Python", state=ComponentState.HEALTHY)]
    )
    plan = planner.build_plan(store, "minimal", include_models=False)
    summary = plan.summary()
    assert summary.get("skip", 0) >= 1
    assert sum(summary.values()) == len(plan.steps)


def test_optional_dep_flagged(win_managers):
    store = _store()
    plan = planner.build_plan(store, "ml-engineer", include_models=False)
    docker = next(s for s in plan.steps if s.key == "docker")
    assert docker.optional is True


def test_config_category_component_ignored_by_plan(win_managers):
    # A CONFIG component with the same key as nothing relevant should not break planning.
    store = _store(
        components=[
            Component(
                key="config:git",
                name="Git config",
                category=Category.CONFIG,
                state=ComponentState.CONFIGURED,
            )
        ]
    )
    plan = planner.build_plan(store, "minimal", include_models=False)
    git = next(s for s in plan.steps if s.key == "git")
    assert git.action == "install"  # config:git != git dependency


def test_by_key_roundtrip():
    assert by_key("minimal").name == "Minimal"
    assert by_key("nope") is None
