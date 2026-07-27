"""Pure helpers for benchmark math and tier heuristics."""

from __future__ import annotations


def throughput_mbps(byte_count: int, seconds: float) -> float:
    """Return megabytes per second for a transfer of ``byte_count`` bytes."""

    if seconds <= 0:
        return 0.0
    return round(byte_count / seconds / (1024 * 1024), 2)


def recommend_tier(
    *,
    cpu_score: float,
    disk_write_mbps: float,
    disk_read_mbps: float,
    ram_gb: float,
    vram_gb: float,
    tokens_per_sec: float | None = None,
) -> dict:
    """Map measured hardware to a model tier consistent with the recommendation engine."""

    score = 0
    if cpu_score >= 2_000_000:
        score += 2
    elif cpu_score >= 500_000:
        score += 1

    disk = max(disk_write_mbps, disk_read_mbps)
    if disk >= 200:
        score += 2
    elif disk >= 50:
        score += 1

    if ram_gb >= 32:
        score += 2
    elif ram_gb >= 16:
        score += 1

    if vram_gb >= 8:
        score += 2
    elif vram_gb >= 4:
        score += 1

    if tokens_per_sec is not None:
        if tokens_per_sec >= 40:
            score += 2
        elif tokens_per_sec >= 15:
            score += 1

    if score >= 7:
        tier = "workstation"
        label = "Large models (13B+) and fast local inference"
    elif score >= 4:
        tier = "mid"
        label = "7B–13B models comfortably"
    elif score >= 2:
        tier = "entry"
        label = "3B–7B models; light coding assistants"
    else:
        tier = "minimal"
        label = "1B–3B models or cloud offload"

    return {"tier": tier, "label": label, "score": score}
