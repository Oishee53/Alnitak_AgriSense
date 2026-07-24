"""Fertilizer & irrigation scheduler (Tier 1).

Quantities and timing by growth stage, organic alternatives, and cost — tied to
the specific crop and soil, and grounded in the KB fertilizer guides.
"""
from __future__ import annotations

from typing import Any


async def build_fertilizer_schedule(
    crop: str,
    soil_type: str,
    farm_size_acres: float,
    weather_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a stage-by-stage fertilizer + irrigation schedule with costs.

    TODO: retrieve dose tables (N-P-K, urea/TSP/MoP kg/acre by stage) from the KB;
    scale by acreage; add organic alternatives; flag weather adjustments (e.g.
    delay nitrogen if heavy rain is forecast — see proactive advice, Tier 1).
    """
    raise NotImplementedError
