"""Crop recommendation tool (Tier-0 #3).

Two-stage, fully deterministic and traceable:
  1. FEASIBILITY GATES — hard-exclude crops that are impossible for the profile
     (wrong season, water need far beyond supply, cost above the whole budget),
     each with a stated reason. Constraints are treated as constraints, not soft
     trade-offs.
  2. RANKING — score the feasible survivors by a blend of agronomic suitability
     and RISK-ADJUSTED expected profit. The farmer can bias this via `priority`
     (balanced / profit / safe).

All numbers come from seed reference data (BRRI/BARC/DAE-derived) + live weather;
the LLM never invents scores. KB citations are attached for grounding.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from app.rag import retriever
from app.tools.seed_data import (
    crop_economics,
    crop_profiles,
    market_prices,
    normalize_season,
    normalize_soil,
)


def current_season(today: date | None = None) -> str:
    """Which cropping season is running right now (by month)."""
    m = (today or date.today()).month
    if 3 <= m <= 5:
        return "kharif-1"
    if 6 <= m <= 10:
        return "kharif-2"
    return "rabi"


_WATER_RANK = {"low": 0, "low-medium": 1, "medium": 2, "high": 3}
# How much water each availability class can support (rank ceiling).
_AVAIL_CEILING = {
    "rainfed": 2,       # rain-dependent: up to "medium" in monsoon
    "limited": 2,       # a few irrigations possible
    "canal": 3,
    "tubewell": 3,
    "reliable": 3,
}

# Expected-value haircut applied to profit for downside risk — used for the
# risk-adjusted profit figure SHOWN to the farmer.
_RISK_FACTOR = {"low": 1.0, "medium": 0.75, "high": 0.55}
# Low-risk preference score — an explicit ranking term so "safe" mode actually
# surfaces low-risk crops even when every crop is agronomically 100% suitable.
_RISK_SCORE = {"low": 1.0, "medium": 0.6, "high": 0.3}
_RISK_ORDER = {"low": 0, "medium": 1, "high": 2}

# Composite ranking weights (suitability, profit, low-risk) per priority.
_PRIORITY_WEIGHTS = {
    "balanced": (0.45, 0.35, 0.20),
    "profit": (0.20, 0.70, 0.10),
    "safe": (0.35, 0.15, 0.50),
}


def _availability_rank(water_availability: str | None, season: str | None) -> int:
    s = (water_availability or "").lower()
    for key, ceil in _AVAIL_CEILING.items():
        if key in s:
            # rainfed outside monsoon can't even support medium-need crops
            if key == "rainfed" and season == "rabi":
                return 1
            return ceil
    return 3 if not s else 2  # unknown → assume moderate


def _crop_price(name: str, econ: dict[str, Any]) -> float:
    mp = market_prices().get(name.split(" (")[0], {})
    return mp.get("current") or econ.get("price_bdt_per_unit", 0)


async def recommend_crops(
    soil_type: str,
    season: str,
    water_availability: str | None = None,
    weather_summary: dict[str, Any] | None = None,
    budget_bdt: float | None = None,
    farm_size_acres: float | None = None,
    priority: str = "balanced",
) -> dict[str, Any]:
    """Return feasible crops ranked by suitability + risk-adjusted profit, plus
    the crops ruled out and why. `priority` biases the ranking:
    'balanced' (default), 'profit' (maximise return), or 'safe' (minimise risk)."""
    soil = normalize_soil(soil_type)
    norm_season = normalize_season(season)
    avail_rank = _availability_rank(water_availability, norm_season)
    acres = farm_size_acres or 1.0
    priority = priority if priority in _PRIORITY_WEIGHTS else "balanced"

    rain = (weather_summary or {}).get("total_rain_mm")

    # A short-range forecast is only decision-relevant if the target season is
    # happening NOW. A July forecast says nothing about January Boro planting.
    now_season = current_season()
    weather_applicable = norm_season == now_season
    weather_gate_note = None
    if rain is not None and not weather_applicable:
        weather_gate_note = (
            f"live forecast NOT factored into ranking: target season "
            f"'{norm_season}' is not the current season ('{now_season}'); the "
            f"forecast horizon does not reach the sowing window"
        )

    scored: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    for name, prof in crop_profiles().items():
        econ = crop_economics().get(name, {})
        in_season = norm_season in prof["seasons"] if norm_season else True
        soil_score = prof["soil"].get(soil, 0.5)
        need_rank = _WATER_RANK.get(prof["water_need"], 2)
        water_gap = need_rank - avail_rank
        cost_per_acre = sum(econ.get("costs_per_acre", {}).values())
        total_cost = cost_per_acre * acres

        # ---------- Stage 1: feasibility gates ----------
        gate_reasons: list[str] = []
        if norm_season and not in_season:
            gate_reasons.append(
                f"out of season — grows in {'/'.join(prof['seasons'])}, not {norm_season}"
            )
        if water_gap >= 2:
            gate_reasons.append(
                f"water need '{prof['water_need']}' far exceeds a "
                f"'{water_availability or 'limited'}' water supply"
            )
        if budget_bdt is not None and cost_per_acre > budget_bdt:
            gate_reasons.append(
                f"costs ~{cost_per_acre:,.0f} BDT/acre — above the entire "
                f"{budget_bdt:,.0f} BDT budget even for 1 acre"
            )

        # ---------- Stage 2: scoring ----------
        water_score = 1.0 if water_gap <= 0 else max(0.0, 1.0 - 0.4 * water_gap)

        weather_note = ""
        weather_adj = 0.0
        if rain is not None and weather_applicable:
            if prof["water_need"] in ("medium", "high") and rain < 10 and avail_rank < 3:
                weather_adj -= 0.1
                weather_note = f"only {rain} mm rain forecast — a stress risk for a {prof['water_need']}-water crop without irrigation"
            elif "waterlog" in prof.get("water_note", "") and rain > 80:
                weather_adj -= 0.15
                weather_note = f"{rain} mm forecast rain raises waterlogging risk"
            elif rain >= 10 and prof["water_need"] in ("medium", "high"):
                weather_note = f"{rain} mm rain forecast over the period supports its {prof['water_need']} water need"

        budget_ok = budget_bdt is None or total_cost <= budget_bdt
        affordable_acres = (
            None if budget_bdt is None or cost_per_acre == 0
            else round(budget_bdt / cost_per_acre, 2)
        )
        budget_score = 1.0 if budget_ok else max(0.3, (budget_bdt or 0) / total_cost if total_cost else 1.0)

        # Feasible crops are all in-season, so suitability weights the remaining
        # agronomic factors (soil, water, budget) over a small base.
        suitability = round(
            max(0.0, min(1.0,
                0.10 + 0.45 * soil_score + 0.30 * water_score + 0.15 * budget_score + weather_adj
            )), 2,
        )

        price = _crop_price(name, econ)
        yield_pa = econ.get("yield_per_acre", 0)
        expected_profit_pa = round(yield_pa * price - cost_per_acre)
        risk_factor = _RISK_FACTOR.get(prof["risk"], 0.75)
        risk_adj_profit_pa = round(expected_profit_pa * risk_factor)

        because_parts = [
            f"{soil} soil suitability {soil_score:.1f}/1.0 ({prof['source']})",
            f"water need '{prof['water_need']}' vs '{water_availability or 'unknown'}' supply",
            f"{prof['risk']} risk → profit discounted ×{risk_factor:g}",
        ]
        if weather_note:
            because_parts.append(weather_note)
        if budget_bdt is not None:
            if budget_ok:
                because_parts.append(f"fits budget (~{total_cost:,.0f} of {budget_bdt:,.0f} BDT for {acres:g} acre)")
            elif affordable_acres:
                because_parts.append(
                    f"full {acres:g} acre needs {total_cost:,.0f} BDT — budget covers ~{affordable_acres:g} acre"
                )

        entry = {
            "crop": name,
            "suitability": suitability,
            "in_season": in_season,
            "water_need": prof["water_need"],
            "risk": prof["risk"],
            "risk_note": prof["risk_note"],
            "sowing_window": prof["sowing_window"]["label"],
            "rough_cost_bdt_per_acre": cost_per_acre,
            "expected_profit_bdt_per_acre": expected_profit_pa,
            "risk_adjusted_profit_bdt_per_acre": risk_adj_profit_pa,
            # kept for backward compatibility with existing UI
            "rough_profit_bdt_per_acre": expected_profit_pa,
            "rough_profit_bdt_total": round(expected_profit_pa * acres),
            "affordable_acres": affordable_acres,
            "because": "; ".join(because_parts),
            "_feasible": not gate_reasons,
        }
        if gate_reasons:
            excluded.append(
                {"crop": name, "reasons": gate_reasons, "water_need": prof["water_need"], "risk": prof["risk"]}
            )
        scored.append(entry)

    # ---------- Rank the feasible pool (fall back to relaxed if none) ----------
    feasible = [e for e in scored if e["_feasible"]]
    relaxed = not feasible
    pool = feasible if feasible else scored

    max_profit = max((e["expected_profit_bdt_per_acre"] for e in pool), default=0)
    w_suit, w_profit, w_risk = _PRIORITY_WEIGHTS[priority]
    for e in pool:
        profit_norm = (
            max(0, e["expected_profit_bdt_per_acre"]) / max_profit if max_profit > 0 else 0.0
        )
        risk_score = _RISK_SCORE.get(e["risk"], 0.6)
        e["profit_norm"] = round(profit_norm, 3)
        e["score"] = round(
            w_suit * e["suitability"] + w_profit * profit_norm + w_risk * risk_score, 3
        )

    pool.sort(
        key=lambda e: (e["score"], -_RISK_ORDER.get(e["risk"], 1)), reverse=True
    )
    top = [{k: v for k, v in e.items() if k != "_feasible"} for e in pool[:5]]

    kb_refs = await retriever.search_compact(
        f"which crop to plant {norm_season or season} season {soil} soil Bangladesh", k=2
    )

    result: dict[str, Any] = {
        "inputs_used": {
            "soil_type": soil,
            "season": norm_season or season,
            "current_season": now_season,
            "weather_applied_to_ranking": weather_applicable,
            "water_availability": water_availability,
            "budget_bdt": budget_bdt,
            "farm_size_acres": acres,
            "priority": priority,
            "weather_summary": weather_summary,
        },
        "options": top,
        "excluded": excluded,
        "kb_references": kb_refs,
        "ranking_method": (
            f"feasibility-gated, then ranked by a {int(w_suit*100)}/{int(w_profit*100)}/"
            f"{int(w_risk*100)} blend of farm suitability, profit, and low-risk "
            f"preference (priority='{priority}'). Profit shown is risk-discounted "
            f"(low×1.0, medium×0.75, high×0.55)."
        ),
        "note": "profit estimates use seeded reference prices (see data/seed) — disclosed as mock",
    }
    if relaxed:
        result["note"] += (
            " | No crop fully satisfied every constraint; showing closest options "
            "with constraints relaxed."
        )
    if weather_gate_note:
        result["weather_note"] = weather_gate_note
    return result
