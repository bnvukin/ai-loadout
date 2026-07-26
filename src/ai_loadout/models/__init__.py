"""Layer 4 - hardware-aware model recommendation.

* :mod:`ai_loadout.models.catalog` — a curated catalog of local models with capability
  ratings and sizes.
* :mod:`ai_loadout.models.recommend` — scores the catalog against detected hardware and
  produces a comparison table plus per-model estimates (tokens/sec, memory, load time).
"""

from .catalog import CATALOG, ModelSpec, get_catalog
from .recommend import Recommendation, estimate, recommend, recommend_for_store

__all__ = [
    "CATALOG",
    "ModelSpec",
    "Recommendation",
    "estimate",
    "get_catalog",
    "recommend",
    "recommend_for_store",
]
