"""Tests for the Tier-1 tools: fertilizer scheduler, pest risk, scenario sim.

These are the parts where a wrong number would mislead a real farmer, so the
tests assert the arithmetic and the grounding rules from the knowledge base
rather than just "it returned something".
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.tools.fertilizer import build_fertilizer_schedule
from app.tools.pests import assess_pest_risk
from app.tools.scenario import simulate


# --------------------------------------------------------------------------
# Fertilizer & irrigation scheduler
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_fertilizer_doses_scale_with_area():
    one = await build_fertilizer_schedule(
        crop="T. Aman Rice", soil_type="loam", farm_size_acres=1.0
    )
    two = await build_fertilizer_schedule(
        crop="T. Aman Rice", soil_type="loam", farm_size_acres=2.0
    )
    # Per-acre doses are area-independent; totals and cost double.
    assert one["seasonal_doses_kg_per_acre"] == two["seasonal_doses_kg_per_acre"]
    assert two["total_fertilizer_cost_bdt"] == pytest.approx(
        one["total_fertilizer_cost_bdt"] * 2, rel=0.01
    )


@pytest.mark.asyncio
async def test_urea_splits_sum_to_the_seasonal_dose():
    """Every kg of urea in the schedule must add up to the seasonal dose —
    the farmer must not be told to apply more (or less) than the KB specifies."""
    res = await build_fertilizer_schedule(
        crop="Maize (Kharif)", soil_type="loam", farm_size_acres=1.0
    )
    scheduled_urea = sum(
        item["kg"]
        for stage in res["fertilizer_schedule"]
        for item in stage["inputs"]
        if item["input"] == "Urea"
    )
    assert scheduled_urea == pytest.approx(res["seasonal_doses_kg_per_acre"]["Urea"], rel=0.01)


@pytest.mark.asyncio
async def test_sandy_soil_raises_mop_per_the_kb_rule():
    """fertilizer_guide.md: sandy soils get 25% extra MoP."""
    loam = await build_fertilizer_schedule(
        crop="T. Aman Rice", soil_type="loam", farm_size_acres=1.0
    )
    sandy = await build_fertilizer_schedule(
        crop="T. Aman Rice", soil_type="sandy", farm_size_acres=1.0
    )
    assert sandy["seasonal_doses_kg_per_acre"]["MoP"] == pytest.approx(
        loam["seasonal_doses_kg_per_acre"]["MoP"] * 1.25, rel=0.01
    )
    assert any("sandy" in a for a in sandy["adjustments_applied"])


@pytest.mark.asyncio
async def test_organic_option_cuts_urea_and_tsp_and_adds_cowdung():
    """KB rule: with 2 t/acre cowdung, cut urea and TSP by about 20%."""
    base = await build_fertilizer_schedule(
        crop="Potato", soil_type="loam", farm_size_acres=1.0
    )
    organic = await build_fertilizer_schedule(
        crop="Potato", soil_type="loam", farm_size_acres=1.0, use_organic=True
    )
    assert organic["seasonal_doses_kg_per_acre"]["Urea"] == pytest.approx(
        base["seasonal_doses_kg_per_acre"]["Urea"] * 0.8, rel=0.01
    )
    assert organic["organic_alternatives"], "expected a cowdung alternative line"


@pytest.mark.asyncio
async def test_heavy_rain_delays_a_urea_topdress():
    """The KB forbids top-dressing urea within 48h of >20 mm rain. With a heavy
    rain day landing on a urea stage, that stage must carry an alert."""
    sowing = date.today()
    # Maize top-dresses urea at 25 DAS — put 45 mm of rain on that exact day.
    rain_day = (sowing + timedelta(days=25)).isoformat()
    res = await build_fertilizer_schedule(
        crop="Maize (Kharif)",
        soil_type="loam",
        farm_size_acres=1.0,
        sowing_date=sowing.isoformat(),
        daily_weather=[{"date": rain_day, "rain_mm": 45.0}],
    )
    alerted = [s for s in res["fertilizer_schedule"] if "weather_alert" in s]
    assert alerted, "expected a heavy-rain alert on the urea top-dress"
    assert "DELAY" in alerted[0]["weather_alert"]


@pytest.mark.asyncio
async def test_unknown_crop_reports_error_not_invented_doses():
    res = await build_fertilizer_schedule(
        crop="dragonfruit", soil_type="loam", farm_size_acres=1.0
    )
    assert "error" in res


@pytest.mark.asyncio
async def test_frg_derived_crop_returns_real_costed_doses():
    """Brinjal's doses come from FRG-2018 p102 (nutrient kg/ha, Medium soil)
    converted with the Appendix-2 nutrient percentages. Check the conversion
    end to end: 68 kg N/ha midpoint / 0.46 N-in-urea / 2.4711 ac-per-ha ≈ 59.8
    kg urea/acre. A silent change to the factors would break this."""
    res = await build_fertilizer_schedule(
        crop="Brinjal", soil_type="loam", farm_size_acres=1.0
    )

    assert res["seasonal_doses_kg_per_acre"]["Urea"] == pytest.approx(59.85, abs=0.2)
    assert res["total_fertilizer_cost_bdt"] > 0
    assert "FRG-2018 p102" in res["source"]
    # FRG puts brinjal N and K in three equal splits at 20/40/60 DAT.
    urea_stages = [
        s for s in res["fertilizer_schedule"]
        if any(i["input"] == "Urea" for i in s["inputs"])
    ]
    assert [s["das"] for s in urea_stages] == [20, 40, 60]


@pytest.mark.asyncio
async def test_crop_without_a_dose_table_gives_timing_but_never_invents_kg():
    """Lentil is ranked by recommend_crops but has no dose table transcribed
    yet. It must still return real timing, and must NOT emit a single kg or BDT
    figure — inventing a dose is the worst failure this tool can have."""
    res = await build_fertilizer_schedule(
        crop="Lentil", soil_type="loam", farm_size_acres=2.0
    )

    assert res.get("doses_available") is False
    assert res["seasonal_doses_kg_per_acre"] == {}
    assert res["cost_breakdown"] == []
    assert res["total_fertilizer_cost_bdt"] is None
    # Real dated stages still come through from the crop calendar.
    assert res["fertilizer_schedule"], "expected timing even without quantities"
    assert all(stage["inputs"] == [] for stage in res["fertilizer_schedule"])
    assert "TIMING ONLY" in res["quantities_note"]
    assert "NOT in our sources" in res["quantities_note"]


def test_every_frg_derived_dose_reconciles_with_its_source_row():
    """Guard the whole derivation: each frg-derived crop stores the FRG nutrient
    row it came from, so every kg/acre figure must be reproducible from that row
    using only the Appendix-2 percentages. This is what lets a judge audit the
    numbers instead of trusting them."""
    import json
    from pathlib import Path

    ref = json.loads(
        (Path(__file__).resolve().parents[1] / "data" / "seed" / "fertilizer_reference.json")
        .read_text(encoding="utf-8")
    )
    deriv = ref["_derivation"]
    acres_per_ha = deriv["acres_per_hectare"]
    comp = deriv["nutrient_composition_pct"]
    nutrient_of = {
        "Urea": ("Urea", "N"),
        "TSP": ("TSP", "P"),
        "MoP": ("MoP", "K"),
        "Gypsum": ("Gypsum", "S"),
        "Zinc sulphate": ("Zinc sulphate", "Zn"),
        "Boric acid": ("Boric acid", "B"),
    }

    checked = 0
    for name, crop in ref["crops"].items():
        if crop.get("provenance") != "frg-derived":
            continue
        src = crop["frg_nutrient_recommendation_kg_per_ha"]
        for product, (comp_key, nutrient) in nutrient_of.items():
            if product not in crop["doses_kg_per_acre"]:
                continue
            low_hi = src[nutrient]
            frac = comp[comp_key][nutrient] / 100
            expected = [(v / frac) / acres_per_ha for v in low_hi]
            actual = crop["doses_kg_per_acre"][product]
            assert actual == pytest.approx(expected, abs=0.15), f"{name} {product}"
            checked += 1

        # Organic fertiliser is stated in t/ha and converted straight to kg/acre.
        assert crop["doses_kg_per_acre"]["Cowdung"][0] == pytest.approx(
            src["OF_t_per_ha"] * 1000 / acres_per_ha, abs=2
        ), f"{name} Cowdung"

        # Split fractions must account for exactly one full seasonal dose.
        totals: dict[str, float] = {}
        for app in crop["applications"]:
            for item, frac_of_dose in app["items"].items():
                totals[item] = totals.get(item, 0) + frac_of_dose
        for item, total in totals.items():
            assert total == pytest.approx(1.0, abs=0.001), f"{name} {item} splits sum to {total}"

    assert checked >= 25, "expected several derived crops to be checked"


# --------------------------------------------------------------------------
# Pest & disease risk
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_pest_risk_filters_by_growth_stage():
    """Fall armyworm threatens maize 20-60 DAS. At 5 DAS it is upcoming, not active."""
    early = await assess_pest_risk(crop="Maize (Kharif)", days_after_sowing=5)
    mid = await assess_pest_risk(crop="Maize (Kharif)", days_after_sowing=30)

    assert any(r["name"].startswith("Fall armyworm") for r in early["upcoming_risks"])
    assert any(r["name"].startswith("Fall armyworm") for r in mid["active_risks"])


@pytest.mark.asyncio
async def test_weather_escalates_risk_to_high():
    """Potato late blight is escalated by a cool humid spell (KB trigger)."""
    dry = await assess_pest_risk(
        crop="Potato",
        days_after_sowing=40,
        weather_summary={"total_rain_mm": 0, "avg_t_max": 26.0, "rain_days": 0},
    )
    foggy = await assess_pest_risk(
        crop="Potato",
        days_after_sowing=40,
        weather_summary={"total_rain_mm": 15, "avg_t_max": 18.0, "rain_days": 5},
    )
    dry_blight = next(r for r in dry["active_risks"] if r["name"] == "Late blight")
    foggy_blight = next(r for r in foggy["active_risks"] if r["name"] == "Late blight")

    assert dry_blight["risk"] == "medium"
    assert foggy_blight["risk"] == "high"
    assert "cool_humid" in foggy["weather_conditions_detected"]


@pytest.mark.asyncio
async def test_pest_treatment_cost_scales_with_area():
    one = await assess_pest_risk(crop="Maize (Kharif)", days_after_sowing=30, farm_size_acres=1)
    three = await assess_pest_risk(crop="Maize (Kharif)", days_after_sowing=30, farm_size_acres=3)
    assert three["protection_budget_bdt"]["high"] == one["protection_budget_bdt"]["high"] * 3


# --------------------------------------------------------------------------
# Scenario simulation
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_rainfall_drop_cuts_yield_and_profit():
    res = await simulate(
        crop="T. Aman Rice",
        farm_size_acres=2.0,
        rainfall_pct=-30,
        water_availability="rainfed",
    )
    assert res["scenario"]["yield_per_acre"] < res["baseline"]["yield_per_acre"]
    assert res["scenario"]["net_profit_bdt"] < res["baseline"]["net_profit_bdt"]
    assert res["net_profit_change_bdt"] < 0
    # The numbers must be internally consistent, not narrated.
    assert res["scenario"]["net_profit_bdt"] == pytest.approx(
        res["scenario"]["revenue_bdt"] - res["scenario"]["total_cost_bdt"]
    )


@pytest.mark.asyncio
async def test_irrigation_buffers_the_rainfall_shock():
    """A tubewell farmer loses less yield to the same rainfall drop than a
    rainfed one — the whole point of asking about water availability."""
    rainfed = await simulate(
        crop="T. Aman Rice", farm_size_acres=1.0, rainfall_pct=-30, water_availability="rainfed"
    )
    irrigated = await simulate(
        crop="T. Aman Rice", farm_size_acres=1.0, rainfall_pct=-30, water_availability="tubewell"
    )
    assert irrigated["scenario"]["yield_per_acre"] > rainfed["scenario"]["yield_per_acre"]


@pytest.mark.asyncio
async def test_budget_cut_reduces_planted_area():
    """A 40% budget cut cannot fund the same acreage — the plan must resize."""
    res = await simulate(crop="Boro Rice", farm_size_acres=2.0, budget_pct=-40)
    assert res["acreage_reduced"] is True
    assert res["scenario"]["farm_size_acres"] < 2.0
    assert res["scenario"]["total_cost_bdt"] < res["baseline"]["total_cost_bdt"]


@pytest.mark.asyncio
async def test_price_rise_lifts_profit_without_touching_cost():
    res = await simulate(crop="Maize (Kharif)", farm_size_acres=1.0, price_pct=20)
    assert res["scenario"]["price_bdt_per_unit"] > res["baseline"]["price_bdt_per_unit"]
    assert res["scenario"]["total_cost_bdt"] == pytest.approx(res["baseline"]["total_cost_bdt"])
    assert res["net_profit_change_bdt"] > 0


@pytest.mark.asyncio
async def test_scenario_requires_a_change():
    res = await simulate(crop="Wheat", farm_size_acres=1.0)
    assert "error" in res


# --------------------------------------------------------------------------
# Weather grounding: the model must never be able to supply its own forecast
# --------------------------------------------------------------------------
def test_weather_params_are_not_advertised_to_the_model():
    """If the schema exposes a weather field, the model can invent one. It must
    only ever arrive via the orchestrator from a real get_weather call."""
    from app.agent.tools import TOOLS

    for name in ("assess_pest_risk", "build_fertilizer_schedule", "recommend_crops"):
        props = TOOLS[name].input_schema.get("properties", {})
        assert "weather_summary" not in props, f"{name} exposes weather_summary to the LLM"
        assert "daily_weather" not in props, f"{name} exposes daily_weather to the LLM"


def test_model_supplied_weather_is_discarded_and_replaced():
    """A hallucinated forecast in the tool call must be thrown away in favour of
    the real one — inventing weather is exactly what the tool must prevent."""
    from app.agent.orchestrator import Orchestrator

    real = {
        "summary": {"total_rain_mm": 34.7, "avg_t_max": 32.4, "rain_days": 5},
        "daily": [{"date": "2026-07-24", "rain_mm": 1.5}],
    }
    params = {
        "crop": "Potato",
        "weather_summary": {"precipitation_sum": 0, "temperature_2m_max": 32},  # invented
        "daily_weather": [{"time": "2026-07-24", "precipitation_sum": 0}],  # invented
    }
    injected = Orchestrator._inject_weather("assess_pest_risk", params, real)

    assert params["weather_summary"] == real["summary"]
    assert params["daily_weather"] == real["daily"]
    assert set(injected) == {"weather_summary", "daily_weather"}


def test_invented_weather_is_dropped_when_no_real_forecast_exists():
    """With no real get_weather result, the model's guess must not slip through
    — the tool should fall back to an honest stage-only answer."""
    from app.agent.orchestrator import Orchestrator

    params = {"crop": "Potato", "weather_summary": {"precipitation_sum": 0}}
    injected = Orchestrator._inject_weather("assess_pest_risk", params, None)

    assert "weather_summary" not in params
    assert injected == []
