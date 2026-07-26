"""The digital twin: a single, live, structured model of the machine.

Everything reads from here and every action updates it *first*, then the UI refreshes.
The store is thread-safe, persists to ``~/.ai-loadout/state.json``, and publishes an
event whenever a component changes so the dashboard can update live.
"""

from __future__ import annotations

import json
import threading
import time

from .. import __version__
from . import paths
from .events import EventBus, EventLevel
from .lifecycle import HEALTH_SCORE, ComponentState, Health, state_to_health
from .models import Component, Hardware, ModelEntry


class StateStore:
    """Holds and persists the machine's digital twin."""

    def __init__(self, bus: EventBus | None = None, autosave: bool = True) -> None:
        self.bus = bus or EventBus()
        self._lock = threading.RLock()
        self._autosave = autosave
        self._hardware: Hardware | None = None
        self._components: dict[str, Component] = {}
        self._models: dict[str, ModelEntry] = {}
        self._meta: dict = {
            "schema": 1,
            "version": __version__,
            "created_ts": time.time(),
            "updated_ts": time.time(),
            "profile": None,
            "capabilities": {},
        }

    # -- hardware ---------------------------------------------------------------------
    def set_hardware(self, hardware: Hardware) -> None:
        with self._lock:
            self._hardware = hardware
            self._touch()
        self.bus.publish(EventLevel.INFO, "Machine scan updated", kind="state", target="hardware")
        self._maybe_save()

    @property
    def hardware(self) -> Hardware | None:
        return self._hardware

    # -- components -------------------------------------------------------------------
    def upsert_component(self, component: Component) -> Component:
        """Insert or replace a component, deriving health from state if left gray."""

        with self._lock:
            if component.health == Health.GRAY and component.state != ComponentState.MISSING:
                component.health = state_to_health(component.state)
            component.updated_ts = time.time()
            self._components[component.key] = component
            self._touch()
        self.bus.publish(
            EventLevel.INFO,
            f"{component.name}: {component.state}",
            kind="state",
            target=component.key,
            state=str(component.state),
            health=str(component.health),
        )
        self._maybe_save()
        return component

    def update_component(self, key: str, **fields) -> Component | None:
        """Patch fields on an existing component (creating a minimal one if needed)."""

        with self._lock:
            component = self._components.get(key)
            if component is None:
                component = Component(key=key, name=fields.get("name", key))
                self._components[key] = component
            for name, value in fields.items():
                if hasattr(component, name):
                    setattr(component, name, value)
            if "state" in fields and "health" not in fields:
                component.health = state_to_health(component.state)
            component.updated_ts = time.time()
            self._touch()
            snapshot = component
        self.bus.publish(
            EventLevel.INFO,
            f"{snapshot.name}: {snapshot.state}",
            kind="state",
            target=key,
            state=str(snapshot.state),
            health=str(snapshot.health),
        )
        self._maybe_save()
        return snapshot

    def get_component(self, key: str) -> Component | None:
        with self._lock:
            return self._components.get(key)

    def components(self) -> list[Component]:
        with self._lock:
            return list(self._components.values())

    # -- models -----------------------------------------------------------------------
    def upsert_model(self, model: ModelEntry) -> ModelEntry:
        with self._lock:
            self._models[model.name] = model
            self._touch()
        self.bus.publish(
            EventLevel.INFO,
            f"Model {model.name} updated",
            kind="state",
            target=f"model:{model.name}",
        )
        self._maybe_save()
        return model

    def models(self) -> list[ModelEntry]:
        with self._lock:
            return list(self._models.values())

    # -- profile / capabilities -------------------------------------------------------
    def set_profile(self, profile: str | None) -> None:
        with self._lock:
            self._meta["profile"] = profile
            self._touch()
        self._maybe_save()

    @property
    def profile(self) -> str | None:
        return self._meta.get("profile")

    # -- health ----------------------------------------------------------------------
    def overall_health(self) -> dict:
        """Aggregate the traffic lights into a single percentage + status label.

        Gray (unknown / not installed) components are excluded from the score so a
        machine with a few optional tools missing does not read as "unhealthy".
        """

        with self._lock:
            components = list(self._components.values())

        scores = [
            HEALTH_SCORE[c.health] for c in components if HEALTH_SCORE.get(c.health) is not None
        ]
        counts = {"green": 0, "yellow": 0, "red": 0, "gray": 0}
        for c in components:
            counts[str(c.health)] = counts.get(str(c.health), 0) + 1

        if not scores:
            percent = 0
            status = "Scanning..."
        else:
            percent = round(100 * sum(scores) / len(scores))
            if counts["red"]:
                status = "Attention needed"
            elif counts["yellow"]:
                status = "Mostly healthy"
            else:
                status = "Everything healthy"
        return {"percent": percent, "status": status, "counts": counts, "total": len(components)}

    # -- serialization ---------------------------------------------------------------
    def snapshot(self) -> dict:
        with self._lock:
            return {
                "meta": dict(self._meta),
                "hardware": self._hardware.to_dict() if self._hardware else None,
                "components": [c.to_dict() for c in self._components.values()],
                "models": [m.to_dict() for m in self._models.values()],
                "health": self.overall_health(),
            }

    def save(self, path=None) -> None:
        paths.ensure_dirs()
        target = path or paths.state_file()
        data = self.snapshot()
        tmp = str(target) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        # Atomic-ish replace so a crash mid-write can't corrupt the state file.
        import os

        os.replace(tmp, target)

    def _maybe_save(self) -> None:
        if self._autosave:
            try:
                self.save()
            except Exception:
                # Persistence is best-effort; never let a disk hiccup break the app.
                pass

    def _touch(self) -> None:
        self._meta["updated_ts"] = time.time()
        self._meta["version"] = __version__


def load_state(bus: EventBus | None = None) -> StateStore:
    """Load a persisted twin from disk, or return a fresh one if none/corrupt.

    The loaded store is a read-friendly reconstruction; detection runs still overwrite
    hardware/components with fresh truth. We reconstruct enough for the dashboard to show
    "last known" state instantly before a rescan finishes.
    """

    store = StateStore(bus=bus)
    file = paths.state_file()
    if not file.exists():
        return store
    try:
        with open(file, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return store

    from .models import Component as _Component  # local import to avoid cycles at top

    meta = data.get("meta") or {}
    store._meta.update({k: meta[k] for k in ("profile", "capabilities") if k in meta})

    hw = data.get("hardware")
    if hw:
        from .models import Disk, Gpu
        from .models import Hardware as _Hardware

        store._hardware = _Hardware(
            os_name=hw.get("os_name", ""),
            os_version=hw.get("os_version", ""),
            os_family=hw.get("os_family", ""),
            arch=hw.get("arch", ""),
            cpu_name=hw.get("cpu_name", ""),
            cpu_cores_physical=hw.get("cpu_cores_physical"),
            cpu_cores_logical=hw.get("cpu_cores_logical"),
            ram_total_gb=hw.get("ram_total_gb"),
            ram_available_gb=hw.get("ram_available_gb"),
            gpus=[
                Gpu(
                    **{
                        k: g.get(k)
                        for k in (
                            "name",
                            "vendor",
                            "vram_total_gb",
                            "vram_free_gb",
                            "driver",
                            "cuda",
                        )
                        if k in g
                    }
                )
                for g in hw.get("gpus", [])
            ],
            disks=[
                Disk(mount=d["mount"], total_gb=d["total_gb"], free_gb=d["free_gb"])
                for d in hw.get("disks", [])
            ],
            primary_disk_free_gb=hw.get("primary_disk_free_gb"),
            is_admin=hw.get("is_admin"),
            virtualization=hw.get("virtualization"),
            internet=hw.get("internet"),
            python_version=hw.get("python_version", ""),
            warnings=hw.get("warnings", []),
        )

    for c in data.get("components", []):
        try:
            store._components[c["key"]] = _Component(
                key=c["key"],
                name=c.get("name", c["key"]),
                category=c.get("category", "dependency"),
                state=ComponentState(c.get("state", "unknown")),
                health=Health(c.get("health", "gray")),
                version=c.get("version"),
                latest_version=c.get("latest_version"),
                path=c.get("path"),
                detail=c.get("detail", ""),
                error=c.get("error"),
                actions=c.get("actions", []),
                depends_on=c.get("depends_on", []),
                optional=c.get("optional", False),
            )
        except Exception:
            continue

    for m in data.get("models", []):
        try:
            store._models[m["name"]] = ModelEntry(
                name=m["name"],
                provider=m.get("provider", "ollama"),
                size_gb=m.get("size_gb"),
                ram_gb=m.get("ram_gb"),
                downloaded=m.get("downloaded", False),
                default=m.get("default", False),
                favorite=m.get("favorite", False),
                detail=m.get("detail", ""),
            )
        except Exception:
            continue

    return store
