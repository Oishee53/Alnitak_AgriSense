"""Pest & disease risk (Tier 1).

Predict likely pests/diseases from crop, growth stage, and live weather, with
preventive + treatment options and estimated cost. Grounded in the KB pest
guides (DAE IPM leaflets, BRRI/BARI plant protection guides), transcribed into
data/seed/pest_reference.json.

Risk is computed, not guessed: a pest is only raised when the crop is inside its
DAS window, and escalated to `high` only when the live forecast matches one of
the KB's stated weather triggers (cool+humid, heavy rain/storm, standing water).
"""
from __future__ import annotations

import json
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.rag import retriever
from app.tools.seed_data import crop_profiles, match_crop_name

_SEED_DIR = Path(__file__).resolve().parents[2] / "data" / "seed"

# KB thresholds: >20 mm/day is the "heavy rain" line used throughout the guides.
_HEAVY_RAIN_MM = 20.0
# "Cool humid" per the blight/aphid rules (potato late blight cites 10–20°C fog).
_COOL_MAX_C = 22.0
_WARM_HUMID_MIN_C = 22.0
# Several rain-days in a week is the KB's "prolonged cloudy humid spell".
_HUMID_RAIN_DAYS = 3


@lru_cache
def _pest_reference() -> dict[str, Any]:
    with open(_SEED_DIR / "pest_reference.json", encoding="utf-8") as fh:
        return json.load(fh)


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


# Growth-stage words the farmer or LLM may use → representative DAS.
_STAGE_DAS = {
    "nursery": -25,
    "land preparation": -7,
    "sowing": 0,
    "planting": 0,
    "transplanting": 0,
    "germination": 7,
    "seedling": 12,
    "establishment": 15,
    "vegetative": 30,
    "tillering": 35,
    "knee-high": 25,
    "branching": 30,
    "bulbing": 45,
    "booting": 70,
    "flowering": 60,
    "tasseling": 45,
    "silking": 55,
    "panicle initiation": 55,
    "heading": 75,
    "podding": 75,
    "fruiting": 90,
    "grain fill": 85,
    "tuber bulking": 50,
    "maturity": 100,
    "harvest": 110,
}


def _resolve_das(
    growth_stage: str | None,
    days_after_sowing: int | None,
    sowing_date: str | None,
) -> tuple[int | None, str]:
    """Work out days-after-sowing from whichever signal the caller supplied."""
    if days_after_sowing is not None:
        return int(days_after_sowing), f"caller-supplied {days_after_sowing} DAS"

    anchor = _parse_date(sowing_date)
    if anchor:
        das = (date.today() - anchor).days
        return das, f"{das} DAS computed from sowing date {anchor.isoformat()}"

    if growth_stage:
        s = growth_stage.strip().lower()
        for key, das in _STAGE_DAS.items():
            if key in s:
                return das, f"growth stage '{growth_stage}' ≈ {das} DAS (typical for that stage)"

    return None, "no growth stage, DAS, or sowing date supplied — showing whole-season risks"


def _weather_conditions(
    weather_summary: dict[str, Any] | None,
    daily_weather: list[dict[str, Any]] | None,
) -> tuple[set[str], list[str]]:
    """Derive which KB weather triggers the live forecast satisfies."""
    conditions: set[str] = set()
    evidence: list[str] = []

    s = weather_summary or {}
    total_rain = s.get("total_rain_mm")
    avg_t_max = s.get("avg_t_max")
    rain_days = s.get("rain_days")

    peak_daily_rain = None
    for d in daily_weather or []:
        mm = d.get("rain_mm")
        if mm is not None:
            peak_daily_rain = mm if peak_daily_rain is None else max(peak_daily_rain, mm)

    if peak_daily_rain is not None and peak_daily_rain >= _HEAVY_RAIN_MM:
        conditions.add("storm_or_heavy_rain")
        evidence.append(f"peak daily rainfall {peak_daily_rain:.0f} mm (≥{_HEAVY_RAIN_MM:.0f} mm heavy-rain line)")
    elif total_rain is not None and total_rain >= 60:
        conditions.add("storm_or_heavy_rain")
        evidence.append(f"{total_rain:.0f} mm total forecast rain over the period")

    if rain_days is not None and rain_days >= _HUMID_RAIN_DAYS:
        if avg_t_max is not None and avg_t_max <= _COOL_MAX_C:
            conditions.add("cool_humid")
            evidence.append(
                f"{rain_days} rain-days with avg max {avg_t_max:.1f}°C — a cool humid spell"
            )
        elif avg_t_max is not None and avg_t_max > _WARM_HUMID_MIN_C:
            conditions.add("warm_humid")
            evidence.append(
                f"{rain_days} rain-days with avg max {avg_t_max:.1f}°C — warm and humid"
            )

    if total_rain is not None and total_rain >= 100:
        conditions.add("standing_water")
        evidence.append(f"{total_rain:.0f} mm forecast rain — fields likely to hold standing water")

    return conditions, evidence


_RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


async def assess_pest_risk(
    crop: str,
    growth_stage: str | None = None,
    days_after_sowing: int | None = None,
    sowing_date: str | None = None,
    weather_summary: dict[str, Any] | None = None,
    daily_weather: list[dict[str, Any]] | None = None,
    farm_size_acres: float | None = None,
) -> dict[str, Any]:
    """Return likely pest/disease risks with prevention, treatment, and cost.

    Pass the `summary` and `daily` objects from get_weather so risk levels
    reflect the real forecast rather than a generic seasonal guess.
    """
    name = match_crop_name(crop)
    if not name:
        return {"error": f"unknown crop '{crop}'", "known_crops": list(crop_profiles().keys())}

    ref = _pest_reference()
    entries = ref["crops"].get(name)
    if not entries:
        return {
            "error": f"no pest reference for '{name}' in the KB",
            "crops_with_pest_data": list(ref["crops"].keys()),
        }

    das, das_basis = _resolve_das(growth_stage, days_after_sowing, sowing_date)
    conditions, weather_evidence = _weather_conditions(weather_summary, daily_weather)
    acres = float(farm_size_acres or 1.0)

    active: list[dict[str, Any]] = []
    upcoming: list[dict[str, Any]] = []

    for e in entries:
        lo, hi = e["das_window"]
        in_window = das is None or lo <= das <= hi
        # A pest is "upcoming" if the crop hasn't reached its window yet.
        ahead = das is not None and das < lo

        # Baseline risk: inside the window it is a live threat; the KB's
        # weather triggers escalate it.
        risk = "medium" if in_window else "low"
        because: list[str] = []
        if das is None:
            because.append(f"active {lo}–{hi} DAS (no current stage given, so listed for the whole season)")
        elif in_window:
            because.append(f"crop is at {das} DAS, inside this pest's {lo}–{hi} DAS window")
        elif ahead:
            because.append(f"crop is at {das} DAS; this becomes a threat from {lo} DAS")
        else:
            because.append(f"crop is at {das} DAS, past this pest's {lo}–{hi} DAS window")

        for trig in e.get("weather_triggers", []):
            if trig["when"] in conditions:
                if in_window and _RISK_ORDER.get(trig["raises_to"], 1) > _RISK_ORDER.get(risk, 1):
                    risk = trig["raises_to"]
                because.append(f"live forecast matches trigger — {trig['because']}")

        cost_lo, cost_hi = e.get("cost_bdt_per_acre", [0, 0])
        entry = {
            "name": e["name"],
            "type": e["type"],
            "risk": risk,
            "das_window": e["das_window"],
            "symptom": e["symptom"],
            "threshold": e.get("threshold"),
            "peak": e.get("peak"),
            "prevention": e.get("prevention", []),
            "treatment": e.get("treatment"),
            "treatment_cost_bdt_per_acre": {"low": cost_lo, "high": cost_hi},
            "treatment_cost_bdt_total": {
                "low": round(cost_lo * acres),
                "high": round(cost_hi * acres),
            },
            "cost_basis": e.get("cost_basis"),
            "because": "; ".join(because),
            "source": e["source"],
        }
        (upcoming if ahead else active).append(entry)

    active.sort(key=lambda x: _RISK_ORDER.get(x["risk"], 1), reverse=True)
    upcoming.sort(key=lambda x: x["das_window"][0])

    # Worst-case protection budget if every currently-active risk needs treating.
    budget_low = sum(x["treatment_cost_bdt_total"]["low"] for x in active)
    budget_high = sum(x["treatment_cost_bdt_total"]["high"] for x in active)

    kb_refs = await retriever.search_compact(f"{name} pest disease management control", k=2)

    return {
        "crop": name,
        "farm_size_acres": acres,
        "growth_stage_input": growth_stage,
        "days_after_sowing": das,
        "stage_basis": das_basis,
        "weather_conditions_detected": sorted(conditions),
        "weather_evidence": weather_evidence
        or ["no live weather passed — risks reflect stage only, not current conditions"],
        "active_risks": active,
        "upcoming_risks": upcoming,
        "protection_budget_bdt": {
            "low": budget_low,
            "high": budget_high,
            "note": (
                f"worst case if every currently-active risk needs treatment across "
                f"{acres:g} acre; IPM/prevention usually costs far less"
            ),
        },
        "general_weather_rules": ref["general_weather_rules"],
        "kb_references": kb_refs,
        "note": (
            "Treatment costs marked 'estimate' in cost_basis are planning figures, "
            "not KB-stated prices — check local dealer rates."
        ),
    }
