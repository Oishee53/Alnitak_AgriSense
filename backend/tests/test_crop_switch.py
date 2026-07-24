"""Crop-switch consistency (orchestrator).

When the farmer changes crop, every crop-keyed panel must move together — no
leftover market/supplier/plan data from the previous crop. Guards the bug where
the season plan updated to Brinjal but market/suppliers still showed Aman.
"""
from __future__ import annotations

from app.agent.orchestrator import _evict_stale_crop_artifacts


def _aman_artifacts() -> dict:
    return {
        "season_plan": {"crop": "T. Aman Rice"},
        "financials": {"crop": "T. Aman Rice"},
        "market": {"crop": "T. Aman Rice", "recommendation": "STORE / WAIT"},
        "suppliers": {"crop": "T. Aman Rice", "best_supplier_id": "SUP002"},
        "fertilizer_schedule": {"crop": "T. Aman Rice"},
        "crop_options": {"options": [{"crop": "T. Aman Rice"}]},  # NOT crop-keyed
    }


def test_switching_crop_evicts_all_other_crops_panels():
    arts = _aman_artifacts()
    arts["season_plan"] = {"crop": "Brinjal"}
    _evict_stale_crop_artifacts(arts, "season_plan", arts["season_plan"])

    assert arts["season_plan"]["crop"] == "Brinjal"
    for slot in ("financials", "market", "suppliers", "fertilizer_schedule"):
        assert slot not in arts, f"{slot} for the old crop should be evicted"


def test_market_for_same_crop_keeps_siblings():
    # Storing a market panel for the SAME crop must not evict the plan/finance.
    arts = {
        "season_plan": {"crop": "Brinjal"},
        "financials": {"crop": "Brinjal"},
    }
    arts["market"] = {"crop": "Brinjal", "recommendation": "SELL NOW"}
    _evict_stale_crop_artifacts(arts, "market", arts["market"])
    assert "season_plan" in arts and "financials" in arts and "market" in arts


def test_crop_options_never_evicted():
    # The ranked crop list is not about one chosen crop; keep it through switches.
    arts = {"crop_options": {"options": []}, "market": {"crop": "Potato"}}
    arts["season_plan"] = {"crop": "Wheat"}
    _evict_stale_crop_artifacts(arts, "season_plan", arts["season_plan"])
    assert "crop_options" in arts
    assert "market" not in arts  # Potato market evicted when Wheat plan lands


def test_missing_crop_field_is_ignored():
    # A panel without a crop field must not crash or trigger eviction.
    arts = {"market": {"crop": "Potato"}}
    _evict_stale_crop_artifacts(arts, "season_plan", {"no_crop": True})
    assert "market" in arts
