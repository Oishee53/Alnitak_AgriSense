"""Season logic + crop recommendation tests.

Covers the KB-aligned season boundaries, rice-season name handling (a farmer
saying "Boro" means Boro Rice — pin it, never silently swap it), and the
honest exclusion path when the requested rice crop is infeasible.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.tools.crops import current_season, recommend_crops
from app.tools.seed_data import normalize_season, season_rice_crop


def test_current_season_matches_kb_definitions():
    # KB (soil_water_suitability.md): Kharif-1 = mid-Mar–Jun, Kharif-2 = Jul–Oct,
    # Rabi = Nov–Feb.
    assert current_season(date(2026, 1, 15)) == "rabi"
    assert current_season(date(2026, 3, 15)) == "kharif-1"
    assert current_season(date(2026, 6, 15)) == "kharif-1"  # June is Kharif-1
    assert current_season(date(2026, 7, 15)) == "kharif-2"
    assert current_season(date(2026, 10, 15)) == "kharif-2"
    assert current_season(date(2026, 11, 15)) == "rabi"


def test_season_normalization_and_rice_intent():
    assert normalize_season("Boro") == "rabi"
    assert normalize_season("Aman") == "kharif-2"
    assert normalize_season("Aus") == "kharif-1"
    assert normalize_season("winter") == "rabi"
    # Rice-season names imply a specific rice crop; neutral names do not.
    assert season_rice_crop("Boro") == "Boro Rice"
    assert season_rice_crop("Aman season") == "T. Aman Rice"
    assert season_rice_crop("Rabi") is None
    assert season_rice_crop("Kharif-2") is None


@pytest.mark.asyncio
async def test_boro_request_pins_boro_rice_first():
    r = await recommend_crops(
        soil_type="loam", season="Boro", water_availability="tubewell",
        budget_bdt=60000, farm_size_acres=2.0,
    )
    assert r["options"], "expected feasible options"
    top = r["options"][0]
    assert top["crop"] == "Boro Rice"
    assert top.get("farmer_requested") is True
    # Alternatives still compete — not a rice-only filter.
    assert len(r["options"]) >= 3
    assert any(o["crop"] != "Boro Rice" for o in r["options"])


@pytest.mark.asyncio
async def test_neutral_rabi_request_pins_nothing():
    r = await recommend_crops(
        soil_type="loam", season="Rabi", water_availability="tubewell",
        budget_bdt=60000, farm_size_acres=2.0,
    )
    assert r["inputs_used"]["requested_crop"] is None
    assert not any(o.get("farmer_requested") for o in r["options"])


@pytest.mark.asyncio
async def test_infeasible_requested_rice_is_explained_not_silently_dropped():
    # Boro is a fully irrigated crop — rainfed-only water rules it out.
    r = await recommend_crops(
        soil_type="loam", season="Boro", water_availability="rainfed",
        budget_bdt=60000, farm_size_acres=2.0,
    )
    assert not any(o.get("farmer_requested") for o in r["options"])
    note = r.get("requested_crop_note", "")
    assert "Boro Rice" in note and "ruled out" in note
