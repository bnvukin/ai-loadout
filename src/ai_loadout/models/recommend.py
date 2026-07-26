"""Turn the catalog + detected hardware into ranked, explained recommendations.

The estimates here are deliberately simple, transparent heuristics -- not a benchmark.
They exist to steer a first choice ("this will be fast / this won't fit"), and the actual
Benchmark layer refines the numbers once a model is installed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.models import Hardware
from .catalog import ModelSpec, get_catalog


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _pick_backend(spec: ModelSpec, vram_gb: float) -> str:
    """gpu = full offload fits, partial = some offload, cpu = no usable GPU."""

    if vram_gb <= 0:
        return "cpu"
    if vram_gb >= spec.size_gb:
        return "gpu"
    if vram_gb >= spec.size_gb * 0.5:
        return "partial"
    return "cpu"


def _fit(spec: ModelSpec, ram_gb: float) -> str:
    """fits = comfortable, tight = will load but cramped, too_big = won't run well."""

    if ram_gb >= spec.min_ram_gb:
        return "fits"
    if ram_gb >= spec.size_gb * 1.2:
        return "tight"
    return "too_big"


def estimate(spec: ModelSpec, hardware: Hardware) -> dict:
    """Estimate tokens/sec, memory, load time and a sensible context length."""

    ram_gb = hardware.ram_total_gb or 0.0
    vram_gb = hardware.total_vram_gb()
    backend = _pick_backend(spec, vram_gb)

    if backend == "gpu":
        tok = _clamp(round(420 / spec.params_b), 6, 130)
    elif backend == "partial":
        tok = _clamp(round(150 / spec.params_b), 3, 45)
    else:
        tok = _clamp(round(60 / spec.params_b), 1, 25)

    est_memory_gb = round(spec.size_gb * 1.15 + 0.7, 1)
    est_load_time_s = int(round(spec.size_gb / 0.8 + 2))

    budget = vram_gb if backend == "gpu" else ram_gb
    headroom = budget - est_memory_gb
    if headroom >= 12:
        context = "64K"
    elif headroom >= 6:
        context = "32K"
    elif headroom >= 2:
        context = "16K"
    else:
        context = "8K"

    return {
        "backend": backend,
        "tokens_per_sec": int(tok),
        "est_memory_gb": est_memory_gb,
        "est_load_time_s": est_load_time_s,
        "context": context,
    }


def _speed_score(tokens_per_sec: int) -> int:
    if tokens_per_sec >= 40:
        return 5
    if tokens_per_sec >= 20:
        return 4
    if tokens_per_sec >= 10:
        return 3
    if tokens_per_sec >= 5:
        return 2
    return 1


@dataclass
class Recommendation:
    spec: ModelSpec
    fit: str  # fits | tight | too_big
    backend: str
    tokens_per_sec: int
    est_memory_gb: float
    est_load_time_s: int
    context: str
    score: float
    effective_speed: int  # 1-5 on THIS machine
    labels: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            **self.spec.to_dict(),
            "fit": self.fit,
            "backend": self.backend,
            "tokens_per_sec": self.tokens_per_sec,
            "est_memory_gb": self.est_memory_gb,
            "est_load_time_s": self.est_load_time_s,
            "context": self.context,
            "score": round(self.score, 1),
            "effective_speed": self.effective_speed,
            "labels": list(self.labels),
            # convenience for UIs
            "recommended": self.labels[0] if self.labels else self.spec.best_for,
        }


def recommend(hardware: Hardware, catalog: list[ModelSpec] | None = None) -> list[Recommendation]:
    """Rank the catalog for this machine (best first)."""

    specs = catalog if catalog is not None else get_catalog()
    ram_gb = hardware.ram_total_gb or 0.0

    recs: list[Recommendation] = []
    for spec in specs:
        est = estimate(spec, hardware)
        fit = _fit(spec, ram_gb)
        quality = (spec.coding + spec.reasoning) / 2
        eff_speed = _speed_score(est["tokens_per_sec"])
        base = quality * 2 + eff_speed  # quality-weighted
        fit_multiplier = {"fits": 1.0, "tight": 0.5, "too_big": 0.05}[fit]
        score = base * fit_multiplier
        recs.append(
            Recommendation(
                spec=spec,
                fit=fit,
                backend=est["backend"],
                tokens_per_sec=est["tokens_per_sec"],
                est_memory_gb=est["est_memory_gb"],
                est_load_time_s=est["est_load_time_s"],
                context=est["context"],
                score=score,
                effective_speed=eff_speed,
            )
        )

    recs.sort(
        key=lambda r: (r.score, (r.spec.coding + r.spec.reasoning), r.tokens_per_sec), reverse=True
    )
    _assign_labels(recs)
    return recs


def _assign_labels(recs: list[Recommendation]) -> None:
    runnable = [r for r in recs if r.fit != "too_big"]
    if not runnable:
        return
    # Best overall: already sorted, so the first runnable is best.
    runnable[0].labels.append("Best Overall")

    fastest = max(runnable, key=lambda r: (r.tokens_per_sec, -r.spec.params_b))
    if "Best Overall" not in fastest.labels:
        fastest.labels.append("Fastest")

    best_coding = max(runnable, key=lambda r: (r.spec.coding, r.tokens_per_sec))
    if not best_coding.labels:
        best_coding.labels.append("Best Coding")

    smallest = min(runnable, key=lambda r: r.spec.size_gb)
    if not smallest.labels:
        smallest.labels.append("Low-end friendly")


def recommend_for_store(store) -> list[Recommendation]:
    """Recommend using the hardware already in the digital twin (scans if absent)."""

    hardware = store.hardware
    if hardware is None:
        from ..detect.system import scan

        hardware = scan(store)
    return recommend(hardware)


# -- rendering helpers ----------------------------------------------------------------
def stars(n: int, filled: str = "*", empty: str = ".") -> str:
    n = max(0, min(5, int(n)))
    return filled * n + empty * (5 - n)


def build_table(recs: list[Recommendation]) -> list[dict]:
    """Rows for the comparison table (model / best-for / ratings / ram / offline / label)."""

    rows = []
    for r in recs:
        rows.append(
            {
                "model": r.spec.name,
                "best_for": r.spec.best_for,
                "coding": r.spec.coding,
                "reasoning": r.spec.reasoning,
                "speed": r.effective_speed,
                "ram_gb": r.spec.min_ram_gb,
                "offline": r.spec.offline,
                "fit": r.fit,
                "tokens_per_sec": r.tokens_per_sec,
                "recommended": r.labels[0] if r.labels else "",
            }
        )
    return rows


def why(hardware: Hardware, rec: Recommendation) -> str:
    """A short human explanation, in the spirit of the product brief."""

    if hardware.gpus and (hardware.gpus[0].vram_total_gb or 0) > 0:
        gpu = hardware.gpus[0]
        machine = f"a {gpu.name} ({gpu.vram_total_gb} GB VRAM) and {hardware.ram_total_gb} GB RAM"
    elif hardware.gpus:
        machine = f"{hardware.gpus[0].name} (integrated) and {hardware.ram_total_gb} GB RAM"
    else:
        machine = f"no discrete GPU and {hardware.ram_total_gb} GB RAM"

    return (
        f"Your machine has {machine}. Running on the {rec.backend.upper()}, "
        f"{rec.spec.name} should produce ~{rec.tokens_per_sec} tokens/sec, "
        f"use about {rec.est_memory_gb} GB, load in ~{rec.est_load_time_s}s, "
        f"and comfortably handle a {rec.context} context."
    )
