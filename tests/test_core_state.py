from ai_loadout.core.events import EventBus
from ai_loadout.core.lifecycle import Category, ComponentState, Health
from ai_loadout.core.models import Component, Disk, Gpu, Hardware
from ai_loadout.core.state import StateStore, load_state


def _sample_hardware():
    return Hardware(
        os_name="Windows 11 Pro",
        os_family="windows",
        arch="AMD64",
        cpu_name="Test CPU",
        cpu_cores_physical=8,
        cpu_cores_logical=16,
        ram_total_gb=32.0,
        ram_available_gb=20.0,
        gpus=[Gpu(name="RTX 4070", vendor="nvidia", vram_total_gb=12.0)],
        disks=[Disk(mount="C:", total_gb=900.0, free_gb=400.0)],
        primary_disk_free_gb=400.0,
        is_admin=True,
    )


def test_upsert_component_emits_state_event_and_derives_health():
    bus = EventBus()
    events = []
    bus.subscribe(events.append)
    store = StateStore(bus=bus, autosave=False)

    store.upsert_component(
        Component(key="git", name="Git", category=Category.DEPENDENCY, state=ComponentState.HEALTHY)
    )
    comp = store.get_component("git")
    assert comp is not None
    assert comp.health == Health.GREEN  # derived from HEALTHY state
    assert any(e.kind == "state" and e.data.get("target") == "git" for e in events)


def test_update_component_patches_fields():
    store = StateStore(autosave=False)
    store.upsert_component(Component(key="python", name="Python", state=ComponentState.MISSING))
    store.update_component("python", state=ComponentState.INSTALLED, version="3.12.10")
    comp = store.get_component("python")
    assert comp.version == "3.12.10"
    assert comp.state == ComponentState.INSTALLED


def test_overall_health_excludes_gray():
    store = StateStore(autosave=False)
    store.upsert_component(Component(key="a", name="A", state=ComponentState.HEALTHY))  # green
    store.upsert_component(
        Component(key="b", name="B", state=ComponentState.NEEDS_UPDATE)
    )  # yellow
    store.upsert_component(
        Component(key="c", name="C", state=ComponentState.MISSING)
    )  # gray -> excluded
    health = store.overall_health()
    # green(1.0) + yellow(0.5) over 2 scored -> 75%
    assert health["percent"] == 75
    assert health["counts"]["gray"] == 1
    assert health["status"] == "Mostly healthy"


def test_save_and_load_roundtrip(loadout_home):
    store = StateStore(autosave=True)
    store.set_hardware(_sample_hardware())
    store.upsert_component(
        Component(
            key="ollama",
            name="Ollama",
            category=Category.RUNTIME,
            state=ComponentState.HEALTHY,
            version="0.1.0",
        )
    )
    store.save()

    reloaded = load_state()
    assert reloaded.hardware is not None
    assert reloaded.hardware.ram_total_gb == 32.0
    assert reloaded.hardware.gpus[0].name == "RTX 4070"
    comp = reloaded.get_component("ollama")
    assert comp is not None
    assert comp.version == "0.1.0"
    assert comp.state == ComponentState.HEALTHY


def test_load_state_missing_file_is_fresh(loadout_home):
    store = load_state()
    assert store.hardware is None
    assert store.components() == []
