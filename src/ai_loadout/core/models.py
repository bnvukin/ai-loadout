"""Dataclasses that make up the digital twin.

Plain stdlib dataclasses (no pydantic) so the core stays dependency-free and trivially
serializable. Everything has a ``to_dict`` for JSON/state persistence and the dashboard.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from .lifecycle import Category, ComponentState, Health, TrustLevel


@dataclass
class Gpu:
    name: str
    vendor: str = "unknown"  # nvidia | amd | intel | apple | unknown
    vram_total_gb: float | None = None
    vram_free_gb: float | None = None
    driver: str | None = None
    cuda: str | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "vendor": self.vendor,
            "vram_total_gb": self.vram_total_gb,
            "vram_free_gb": self.vram_free_gb,
            "driver": self.driver,
            "cuda": self.cuda,
        }


@dataclass
class Disk:
    mount: str
    total_gb: float
    free_gb: float

    def to_dict(self) -> dict:
        return {"mount": self.mount, "total_gb": self.total_gb, "free_gb": self.free_gb}


@dataclass
class Hardware:
    """Result of Layer 1 machine validation."""

    os_name: str = ""
    os_version: str = ""
    os_family: str = ""  # windows | macos | linux
    arch: str = ""
    cpu_name: str = ""
    cpu_cores_physical: int | None = None
    cpu_cores_logical: int | None = None
    ram_total_gb: float | None = None
    ram_available_gb: float | None = None
    gpus: list[Gpu] = field(default_factory=list)
    disks: list[Disk] = field(default_factory=list)
    primary_disk_free_gb: float | None = None
    is_admin: bool | None = None
    virtualization: bool | None = None
    internet: bool | None = None
    python_version: str = ""
    hostname_present: bool = True  # we intentionally do NOT store the hostname value
    warnings: list[str] = field(default_factory=list)
    scanned_ts: float = field(default_factory=time.time)

    def total_vram_gb(self) -> float:
        return sum((g.vram_total_gb or 0.0) for g in self.gpus)

    def has_gpu(self) -> bool:
        return any((g.vram_total_gb or 0) > 0 for g in self.gpus)

    def to_dict(self) -> dict:
        return {
            "os_name": self.os_name,
            "os_version": self.os_version,
            "os_family": self.os_family,
            "arch": self.arch,
            "cpu_name": self.cpu_name,
            "cpu_cores_physical": self.cpu_cores_physical,
            "cpu_cores_logical": self.cpu_cores_logical,
            "ram_total_gb": self.ram_total_gb,
            "ram_available_gb": self.ram_available_gb,
            "gpus": [g.to_dict() for g in self.gpus],
            "disks": [d.to_dict() for d in self.disks],
            "primary_disk_free_gb": self.primary_disk_free_gb,
            "is_admin": self.is_admin,
            "virtualization": self.virtualization,
            "internet": self.internet,
            "python_version": self.python_version,
            "total_vram_gb": self.total_vram_gb(),
            "warnings": list(self.warnings),
            "scanned_ts": self.scanned_ts,
        }


@dataclass
class Component:
    """A managed thing: a dependency, a runtime, an editor, a service, a connection."""

    key: str
    name: str
    category: Category = Category.DEPENDENCY
    state: ComponentState = ComponentState.UNKNOWN
    health: Health = Health.GRAY
    version: str | None = None
    latest_version: str | None = None
    path: str | None = None
    detail: str = ""
    error: str | None = None
    actions: list[str] = field(default_factory=list)  # e.g. ["install", "update", "repair"]
    depends_on: list[str] = field(default_factory=list)  # keys of prerequisites
    trust: TrustLevel = TrustLevel.SAFE
    optional: bool = False
    updated_ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "category": str(self.category),
            "state": str(self.state),
            "health": str(self.health),
            "version": self.version,
            "latest_version": self.latest_version,
            "path": self.path,
            "detail": self.detail,
            "error": self.error,
            "actions": list(self.actions),
            "depends_on": list(self.depends_on),
            "trust": str(self.trust),
            "optional": self.optional,
            "updated_ts": self.updated_ts,
        }


@dataclass
class ModelEntry:
    """A local model (Layer 4/5) tracked in the twin."""

    name: str
    provider: str = "ollama"
    size_gb: float | None = None
    ram_gb: float | None = None
    downloaded: bool = False
    default: bool = False
    favorite: bool = False
    detail: str = ""
    updated_ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "provider": self.provider,
            "size_gb": self.size_gb,
            "ram_gb": self.ram_gb,
            "downloaded": self.downloaded,
            "default": self.default,
            "favorite": self.favorite,
            "detail": self.detail,
            "updated_ts": self.updated_ts,
        }
