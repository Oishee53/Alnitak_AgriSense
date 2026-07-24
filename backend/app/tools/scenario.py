"""Scenario simulation (Tier 1).

"What if rainfall drops 30%?" / "What if my budget is cut 40%?" — returns a
REVISED plan with changed numbers, not a generic answer. Re-runs the real
finance and crop tools with perturbed inputs and diffs every figure, so the
farmer sees exactly what moved and by how much.

Rainfall→yield sensitivity uses each crop's KB water_need class: a high-water
crop loses far more yield per mm of missing rain than a drought-tolerant one.
"""
from __future__ import annotations

from typing import Any

from app.tools import crops as crops_tool
from app.tools.finance import compute_financials
from app.tools.seed_data import (
    crop_economics,
    crop_profiles,
    match_crop_name,
    normalize_season,
)

# How much of a rainfall shortfall translates into yield loss, by the crop's
# water-need class. A "high" water-need crop (Boro rice) is hit hardest when
# rain fails; a "low" need crop (lentil, mustard) barely notices.
# Irrigation access buffers this — a farmer with a tubewell can replace rain.
_RAIN_SENSITIVITY = {"high": 0.9, "medium": 0.6, "low-medium": 0.35, "low": 0.2}

# Irrigation buffering: fraction of the rainfall shock the farmer can offset by
# irrigating instead. Rainfed farmers absorb the whole shock.
_IRRIGATION_BUFFER = {
    "rainfed": 0.0,
    "limited": 0.3,
    "canal": 0.7,
    "tubewell": 0.85,
    "reliable": 0.85,
}


def _buffer_for(water_availability: str | None) -> tuple[float, str]:
    s = (water_availability or "").lower()
    for key, buf in _IRRIGATION_BUFFER.items():
        if key in s:
            return buf, key
    return 0.0, "rainfed (assumed — no water source on file)"


def _pct(before: float | None, after: float | None) -> float | None:
    if before in (None, 0) or after is None:
        return None
    return round((after - before) / abs(before) * 100, 1)


def _diff(label: str, before: Any, after: Any, unit: str = "BDT") -> dict[str, Any]:
    return {
        "metric": label,
        "before": before,
        "after": after,
        "change": (
            round(after - before, 2)
            if isinstance(before, (int, float)) and isinstance(after, (int, float))
            else None
        ),
        "change_pct": _pct(before, after)
        if isinstance(before, (int, float)) and isinstance(after, (int, float))
        else None,
        "unit": unit,
    }


async def simulate(
    crop: str,
    farm_size_acres: float,
    rainfall_pct: float | None = None,
    budget_pct: float | None = None,
    price_pct: float | None = None,
    yield_pct: float | None = None,
    cost_pct: float | None = None,
    new_budget_bdt: float | None = None,
    water_availability: str | None = None,
    soil_type: str | None = None,
    season: str | None = None,
) -> dict[str, Any]:
    """Apply a what-if change and return {baseline, scenario, deltas, advice}.

    Percentages are signed deltas: rainfall_pct=-30 means "rainfall drops 30%",
    price_pct=15 means "price rises 15%". Every number in `scenario` is produced
    by re-running compute_financials — none are estimated by the model.
    """
    name = match_crop_name(crop)
    if not name:
        return {"error": f"unknown crop '{crop}'", "known_crops": list(crop_profiles().keys())}

    econ = crop_economics().get(name)
    prof = crop_profiles().get(name)
    if not econ or not prof:
        return {"error": f"no reference economics for '{name}'"}

    if all(v is None for v in (rainfall_pct, budget_pct, price_pct, yield_pct, cost_pct, new_budget_bdt)):
        return {
            "error": "no scenario change given",
            "hint": (
                "pass at least one of rainfall_pct, budget_pct, price_pct, "
                "yield_pct, cost_pct, or new_budget_bdt"
            ),
        }

    # ---------- Baseline: the real, unperturbed projection ----------
    baseline = await compute_financials(crop=name, farm_size_acres=farm_size_acres)
    if "error" in baseline:
        return baseline

    base_yield_pa = econ["yield_per_acre"]
    base_price = baseline["price_bdt_per_unit"]
    reasoning: list[str] = []

    # ---------- Apply each perturbation to the real inputs ----------
    sim_acres = farm_size_acres
    sim_yield_pa = float(base_yield_pa)
    sim_price = float(base_price)
    cost_overrides: dict[str, Any] | None = None

    # -- Rainfall shock → yield loss, damped by irrigation access --
    if rainfall_pct is not None:
        buffer, buffer_label = _buffer_for(water_availability)
        sensitivity = _RAIN_SENSITIVITY.get(prof["water_need"], 0.6)
        effective_shock = (rainfall_pct / 100.0) * sensitivity * (1 - buffer)
        sim_yield_pa = round(sim_yield_pa * (1 + effective_shock), 2)
        reasoning.append(
            f"Rainfall {rainfall_pct:+.0f}% → yield {effective_shock * 100:+.1f}%: "
            f"{name} is a '{prof['water_need']}' water-need crop (sensitivity "
            f"{sensitivity:g}), and '{buffer_label}' water access offsets "
            f"{buffer:.0%} of the shortfall ({prof['source']})."
        )

    # -- Direct yield override (e.g. "what if yield drops 20%?") --
    if yield_pct is not None:
        sim_yield_pa = round(sim_yield_pa * (1 + yield_pct / 100.0), 2)
        reasoning.append(f"Yield adjusted {yield_pct:+.0f}% as asked.")

    # -- Price shock --
    if price_pct is not None:
        sim_price = round(sim_price * (1 + price_pct / 100.0), 2)
        reasoning.append(
            f"Selling price {price_pct:+.0f}% → {sim_price:,.0f} BDT/maund "
            f"(baseline {base_price:,.0f})."
        )

    # -- Input-cost inflation --
    if cost_pct is not None:
        cost_overrides = {
            item: {"qty": round(farm_size_acres, 2), "unit_cost": round(per_acre * (1 + cost_pct / 100.0), 2)}
            for item, per_acre in econ["costs_per_acre"].items()
        }
        reasoning.append(f"Every input cost line moved {cost_pct:+.0f}%.")

    # -- Budget cut → the farmer can only plant the acreage they can fund --
    cost_per_acre = sum(econ["costs_per_acre"].values())
    if cost_pct is not None:
        cost_per_acre = cost_per_acre * (1 + cost_pct / 100.0)

    budget_after: float | None = None
    if new_budget_bdt is not None:
        budget_after = float(new_budget_bdt)
    elif budget_pct is not None:
        base_budget = cost_per_acre * farm_size_acres
        budget_after = base_budget * (1 + budget_pct / 100.0)
        reasoning.append(
            f"Budget {budget_pct:+.0f}% → {budget_after:,.0f} BDT (baseline plan needed "
            f"{base_budget:,.0f} BDT for {farm_size_acres:g} acre)."
        )

    acreage_cut = False
    if budget_after is not None and cost_per_acre > 0:
        affordable = budget_after / cost_per_acre
        if affordable < farm_size_acres:
            sim_acres = round(affordable, 2)
            acreage_cut = True
            reasoning.append(
                f"At {cost_per_acre:,.0f} BDT/acre, that budget funds only "
                f"{sim_acres:g} of the {farm_size_acres:g} acre — the plan is resized, "
                f"not just re-priced."
            )
        else:
            reasoning.append(
                f"The budget still covers all {farm_size_acres:g} acre "
                f"({cost_per_acre * farm_size_acres:,.0f} BDT needed) — acreage unchanged."
            )

    # Rescale caller cost overrides to the (possibly reduced) acreage.
    if cost_overrides is not None and sim_acres != farm_size_acres:
        cost_overrides = {
            item: {"qty": round(sim_acres, 2), "unit_cost": spec["unit_cost"]}
            for item, spec in cost_overrides.items()
        }

    # ---------- Re-run the REAL finance engine with perturbed inputs ----------
    scenario = await compute_financials(
        crop=name,
        farm_size_acres=sim_acres,
        inputs=cost_overrides,
        expected_price_bdt_per_unit=sim_price if sim_price != base_price else None,
        expected_yield_per_acre=sim_yield_pa if sim_yield_pa != base_yield_pa else None,
    )
    if "error" in scenario:
        return scenario

    deltas = [
        _diff("Planted area", farm_size_acres, sim_acres, "acre"),
        _diff("Yield per acre", base_yield_pa, sim_yield_pa, baseline["expected_yield_unit"]),
        _diff("Total yield", baseline["expected_yield"], scenario["expected_yield"], baseline["expected_yield_unit"]),
        _diff("Price", base_price, scenario["price_bdt_per_unit"], "BDT/" + baseline["expected_yield_unit"]),
        _diff("Total cost", baseline["total_cost_bdt"], scenario["total_cost_bdt"]),
        _diff("Revenue", baseline["revenue_bdt"], scenario["revenue_bdt"]),
        _diff("Net profit", baseline["net_profit_bdt"], scenario["net_profit_bdt"]),
        _diff("ROI", baseline["roi"], scenario["roi"], "ratio"),
        _diff(
            "Break-even price",
            baseline["break_even_price_bdt_per_unit"],
            scenario["break_even_price_bdt_per_unit"],
            "BDT/" + baseline["expected_yield_unit"],
        ),
    ]
    changed = [d for d in deltas if d["change"] not in (None, 0)]

    # ---------- Verdict + a concrete alternative when the scenario hurts ----------
    profit_before = baseline["net_profit_bdt"]
    profit_after = scenario["net_profit_bdt"]
    profit_delta = round(profit_after - profit_before, 2)

    if profit_after < 0 <= profit_before:
        verdict = "This scenario turns a profit into a LOSS."
    elif profit_delta < 0:
        verdict = f"Still profitable, but {abs(profit_delta):,.0f} BDT worse off."
    elif profit_delta > 0:
        verdict = f"Better off by {profit_delta:,.0f} BDT under this scenario."
    else:
        verdict = "No change to the bottom line."

    alternatives: list[dict[str, Any]] = []
    if profit_delta < 0 and (rainfall_pct is not None or budget_after is not None):
        # Offer real, re-ranked alternatives under the changed constraint rather
        # than a generic "consider other crops".
        alt = await crops_tool.recommend_crops(
            soil_type=soil_type or "loam",
            season=season or (prof["seasons"][0] if prof.get("seasons") else "kharif-2"),
            water_availability=water_availability,
            budget_bdt=budget_after,
            farm_size_acres=farm_size_acres,
            priority="safe" if rainfall_pct is not None else "balanced",
        )
        for opt in alt.get("options", [])[:3]:
            if opt["crop"] == name:
                continue
            alternatives.append(
                {
                    "crop": opt["crop"],
                    "suitability": opt["suitability"],
                    "risk": opt["risk"],
                    "water_need": opt["water_need"],
                    "cost_bdt_per_acre": opt["rough_cost_bdt_per_acre"],
                    "risk_adjusted_profit_bdt_per_acre": opt["risk_adjusted_profit_bdt_per_acre"],
                    "affordable_acres": opt.get("affordable_acres"),
                    "because": opt["because"],
                }
            )

    return {
        "crop": name,
        "scenario_applied": {
            k: v
            for k, v in {
                "rainfall_pct": rainfall_pct,
                "budget_pct": budget_pct,
                "new_budget_bdt": new_budget_bdt,
                "price_pct": price_pct,
                "yield_pct": yield_pct,
                "cost_pct": cost_pct,
            }.items()
            if v is not None
        },
        "baseline": {
            "farm_size_acres": farm_size_acres,
            "yield_per_acre": base_yield_pa,
            "total_yield": baseline["expected_yield"],
            "price_bdt_per_unit": base_price,
            "total_cost_bdt": baseline["total_cost_bdt"],
            "revenue_bdt": baseline["revenue_bdt"],
            "net_profit_bdt": baseline["net_profit_bdt"],
            "roi": baseline["roi"],
            "break_even_price_bdt_per_unit": baseline["break_even_price_bdt_per_unit"],
        },
        "scenario": {
            "farm_size_acres": sim_acres,
            "yield_per_acre": sim_yield_pa,
            "total_yield": scenario["expected_yield"],
            "price_bdt_per_unit": scenario["price_bdt_per_unit"],
            "total_cost_bdt": scenario["total_cost_bdt"],
            "revenue_bdt": scenario["revenue_bdt"],
            "net_profit_bdt": scenario["net_profit_bdt"],
            "roi": scenario["roi"],
            "break_even_price_bdt_per_unit": scenario["break_even_price_bdt_per_unit"],
        },
        "deltas": deltas,
        "changed_metrics": [d["metric"] for d in changed],
        "acreage_reduced": acreage_cut,
        "verdict": verdict,
        "net_profit_change_bdt": profit_delta,
        "reasoning": reasoning,
        "alternatives_under_new_constraint": alternatives,
        "assumptions": scenario["assumptions"],
        "note": (
            "Baseline and scenario are both produced by compute_financials — the "
            "same deterministic math, only the inputs differ."
        ),
    }
