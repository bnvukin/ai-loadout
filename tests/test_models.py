from ai_loadout.core.models import Gpu, Hardware
from ai_loadout.models import catalog
from ai_loadout.models.recommend import (
    build_table,
    estimate,
    recommend,
    stars,
    why,
)


def _low_end():
    return Hardware(os_family="windows", ram_total_gb=8.0, ram_available_gb=4.0, cpu_name="CPU")


def _mid_no_gpu():
    return Hardware(os_family="windows", ram_total_gb=32.0, ram_available_gb=16.0, cpu_name="CPU")


def _gpu_workstation():
    return Hardware(
        os_family="windows",
        ram_total_gb=64.0,
        ram_available_gb=48.0,
        cpu_name="CPU",
        gpus=[Gpu(name="NVIDIA GeForce RTX 4090", vendor="nvidia", vram_total_gb=24.0)],
    )


def test_catalog_schema_is_valid():
    seen = set()
    assert catalog.CATALOG, "catalog must not be empty"
    for spec in catalog.CATALOG:
        assert spec.key not in seen, f"duplicate key {spec.key}"
        seen.add(spec.key)
        assert spec.params_b > 0
        assert spec.size_gb > 0
        assert spec.min_ram_gb > 0
        for rating in (spec.coding, spec.reasoning, spec.speed):
            assert 1 <= rating <= 5
        assert spec.tag and spec.name and spec.best_for


def test_estimate_gpu_is_faster_than_cpu():
    spec = catalog.by_key("qwen3-8b")
    gpu_est = estimate(spec, _gpu_workstation())
    cpu_est = estimate(spec, _mid_no_gpu())
    assert gpu_est["backend"] == "gpu"
    assert cpu_est["backend"] == "cpu"
    assert gpu_est["tokens_per_sec"] > cpu_est["tokens_per_sec"]
    assert gpu_est["est_memory_gb"] > 0


def test_low_end_machine_excludes_huge_models():
    recs = recommend(_low_end())
    by_key = {r.spec.key: r for r in recs}
    assert by_key["llama3.3-70b"].fit == "too_big"
    assert by_key["qwen3-32b"].fit == "too_big"
    # the top recommendation must be something that actually runs
    assert recs[0].fit != "too_big"
    assert recs[0].spec.min_ram_gb <= 8


def test_mid_machine_recommends_8b_class_first():
    recs = recommend(_mid_no_gpu())
    top = recs[0]
    assert top.fit == "fits"
    assert "Best Overall" in top.labels
    # 70B should not be runnable on 32 GB
    huge = next(r for r in recs if r.spec.key == "llama3.3-70b")
    assert huge.fit == "too_big"


def test_labels_are_assigned_once_each():
    recs = recommend(_gpu_workstation())
    all_labels = [label for r in recs for label in r.labels]
    assert "Best Overall" in all_labels
    # No model carries duplicate label text
    for r in recs:
        assert len(r.labels) == len(set(r.labels))


def test_build_table_and_stars_and_why():
    recs = recommend(_gpu_workstation())
    table = build_table(recs)
    assert len(table) == len(recs)
    assert set(table[0]).issuperset({"model", "best_for", "coding", "ram_gb", "fit"})
    assert stars(3) == "***.."
    assert stars(9) == "*****"  # clamped
    text = why(_gpu_workstation(), recs[0])
    assert "tokens/sec" in text and "RTX 4090" in text


def test_recommendation_to_dict_has_recommended_field():
    recs = recommend(_mid_no_gpu())
    d = recs[0].to_dict()
    assert "recommended" in d and d["recommended"]
    assert d["tokens_per_sec"] >= 1
