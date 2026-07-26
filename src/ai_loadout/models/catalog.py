"""A curated catalog of local models Loadout can recommend and pull.

Sizes are approximate on-disk sizes for the common 4-bit (Q4_K_M) quantization used by
Ollama; ``min_ram_gb`` is the RAM at which the model runs *comfortably* (not the absolute
floor). Capability ratings (1-5) are coarse, opinionated guidance -- good enough to steer
a first choice, and easy to tune via PRs.

Everything here is data, so it is trivial to extend. A test validates the schema.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    key: str  # stable id
    name: str  # display name
    tag: str  # ollama pull tag
    family: str
    params_b: float  # parameters in billions
    size_gb: float  # approx Q4 on-disk size
    min_ram_gb: float  # comfortable RAM
    min_vram_gb: float  # VRAM for full GPU offload (0 = fine on CPU)
    coding: int  # 1-5
    reasoning: int  # 1-5
    speed: int  # 1-5 (general indicator; recommendation re-scores per hardware)
    best_for: str
    offline: bool = True
    provider: str = "ollama"

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "tag": self.tag,
            "family": self.family,
            "params_b": self.params_b,
            "size_gb": self.size_gb,
            "min_ram_gb": self.min_ram_gb,
            "min_vram_gb": self.min_vram_gb,
            "coding": self.coding,
            "reasoning": self.reasoning,
            "speed": self.speed,
            "best_for": self.best_for,
            "offline": self.offline,
            "provider": self.provider,
        }


# Ordered small -> large. Tags are real Ollama tags at time of writing.
CATALOG: list[ModelSpec] = [
    ModelSpec(
        "llama3.2-3b",
        "Llama 3.2 3B",
        "llama3.2:3b",
        "llama",
        3.0,
        2.0,
        8,
        3,
        coding=3,
        reasoning=3,
        speed=5,
        best_for="Low-end PCs",
    ),
    ModelSpec(
        "phi3.5",
        "Phi-3.5 Mini",
        "phi3.5",
        "phi",
        3.8,
        2.2,
        8,
        3,
        coding=3,
        reasoning=3,
        speed=5,
        best_for="Lightweight",
    ),
    ModelSpec(
        "gemma3-4b",
        "Gemma 3 4B",
        "gemma3:4b",
        "gemma",
        4.0,
        3.3,
        8,
        4,
        coding=4,
        reasoning=4,
        speed=5,
        best_for="Fast assistant",
    ),
    ModelSpec(
        "qwen2.5-coder-7b",
        "Qwen2.5 Coder 7B",
        "qwen2.5-coder:7b",
        "qwen",
        7.0,
        4.7,
        8,
        6,
        coding=5,
        reasoning=4,
        speed=4,
        best_for="Coding (compact)",
    ),
    ModelSpec(
        "llama3.1-8b",
        "Llama 3.1 8B",
        "llama3.1:8b",
        "llama",
        8.0,
        4.9,
        10,
        6,
        coding=4,
        reasoning=4,
        speed=3,
        best_for="General purpose (stable)",
    ),
    ModelSpec(
        "qwen3-8b",
        "Qwen3 8B",
        "qwen3:8b",
        "qwen",
        8.0,
        5.2,
        10,
        6,
        coding=5,
        reasoning=5,
        speed=4,
        best_for="Everyday use",
    ),
    ModelSpec(
        "gemma3-12b",
        "Gemma 3 12B",
        "gemma3:12b",
        "gemma",
        12.0,
        8.1,
        16,
        10,
        coding=4,
        reasoning=4,
        speed=3,
        best_for="Balanced quality",
    ),
    ModelSpec(
        "deepseek-coder-v2-16b",
        "DeepSeek Coder V2 16B",
        "deepseek-coder-v2:16b",
        "deepseek",
        16.0,
        8.9,
        16,
        11,
        coding=5,
        reasoning=4,
        speed=3,
        best_for="Best coding",
    ),
    ModelSpec(
        "qwen3-14b",
        "Qwen3 14B",
        "qwen3:14b",
        "qwen",
        14.0,
        9.3,
        16,
        11,
        coding=5,
        reasoning=5,
        speed=3,
        best_for="High-quality reasoning",
    ),
    ModelSpec(
        "qwen3-32b",
        "Qwen3 32B",
        "qwen3:32b",
        "qwen",
        32.0,
        20.0,
        32,
        22,
        coding=5,
        reasoning=5,
        speed=2,
        best_for="Max quality (big machines)",
    ),
    ModelSpec(
        "llama3.3-70b",
        "Llama 3.3 70B",
        "llama3.3:70b",
        "llama",
        70.0,
        43.0,
        64,
        42,
        coding=5,
        reasoning=5,
        speed=1,
        best_for="Frontier (workstation/GPU)",
    ),
]


def get_catalog() -> list[ModelSpec]:
    """Return a copy of the catalog (so callers can sort/filter freely)."""

    return list(CATALOG)


def by_key(key: str) -> ModelSpec | None:
    for spec in CATALOG:
        if spec.key == key:
            return spec
    return None
