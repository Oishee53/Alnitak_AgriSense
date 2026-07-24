"""Supplier comparison tests (Tier 2).

Deterministic over the seed catalog — no network. Pin the needs sizing (FRG
midpoints × acres), the sandy-soil MoP bump, the cheapest-first ranking with
savings, and the graceful no-dose-table path.
"""
from __future__ import annotations

import pytest

from app.tools.suppliers import compare_suppliers


@pytest.mark.asyncio
async def test_needs_sized_from_frg_midpoints():
    # T. Aman rice doses/acre: Urea[60,70]→65, TSP[20,25]→22.5, MoP[25,30]→27.5.
    # ×2 acres → urea 130, tsp 45, mop 55.
    r = await compare_suppliers("T. Aman Rice", 2, "loam")
    assert r["needs_kg"]["urea_kg"] == 130.0
    assert r["needs_kg"]["tsp_kg"] == 45.0
    assert r["needs_kg"]["mop_kg"] == 55.0


@pytest.mark.asyncio
async def test_ranked_cheapest_first_with_savings():
    r = await compare_suppliers("T. Aman Rice", 2, "loam")
    totals = [s["total_input_cost_bdt"] for s in r["suppliers"]]
    assert totals == sorted(totals)  # cheapest first
    assert r["best_supplier_id"] == r["suppliers"][0]["id"]
    assert r["savings_vs_worst_bdt"] == totals[-1] - totals[0]


@pytest.mark.asyncio
async def test_sandy_soil_bumps_mop_25pct():
    loam = await compare_suppliers("T. Aman Rice", 2, "loam")
    sandy = await compare_suppliers("T. Aman Rice", 2, "sandy")
    # +25% MoP, allowing for the 1-decimal rounding on the sized quantity.
    assert sandy["needs_kg"]["mop_kg"] == pytest.approx(
        loam["needs_kg"]["mop_kg"] * 1.25, abs=0.1
    )
    # urea/tsp unchanged
    assert sandy["needs_kg"]["urea_kg"] == loam["needs_kg"]["urea_kg"]


@pytest.mark.asyncio
async def test_line_costs_match_qty_times_price():
    r = await compare_suppliers("Boro Rice", 3, "loam")
    for sup in r["suppliers"]:
        computed = sum(l["line_cost_bdt"] for l in sup["lines"])
        assert computed == sup["total_input_cost_bdt"]
        for line in sup["lines"]:
            assert line["line_cost_bdt"] == round(
                line["qty_kg"] * line["price_bdt_per_kg"]
            )


@pytest.mark.asyncio
async def test_catalog_disclosed_as_mock():
    r = await compare_suppliers("Potato", 1, "loam")
    assert "mock" in r["catalog_source"].lower() or "seed" in r["catalog_source"].lower()


@pytest.mark.asyncio
async def test_no_dose_table_crop_errors_gracefully():
    # Sugarcane has no kg/acre dose table → can't size the basket.
    r = await compare_suppliers("Sugarcane", 1, "loam")
    assert "error" in r
    assert r["crops_with_tables"]
