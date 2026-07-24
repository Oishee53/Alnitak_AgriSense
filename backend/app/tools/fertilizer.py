"""Fertilizer & irrigation scheduler (Tier 1).

Quantities and timing by growth stage, organic alternatives, and cost — tied to
the specific crop and soil, and grounded in the KB fertilizer guides
(BARC FRG-2018 / DAE leaflets, transcribed into data/seed/fertilizer_reference.json).

Everything here is deterministic arithmetic over the reference doses. The LLM
never invents a kg or a taka figure; it repeats what this tool returns, and the
`because`/`source` fields let a judge trace every number back to the KB.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.rag import retriever
from app.tools.seed_data import crop_profiles, match_crop_name, normalize_soil

_SEED_DIR = Path(__file__).resolve().parents[2] / "data" / "seed"

# Heavy-rain threshold (mm/day) at which urea top-dressing should be delayed —
# straight from fertilizer_guide.md "Weather rules for fertilizer timing".
_HEAVY_RAIN_MM = 20.0


@lru_cache
def _fertilizer_reference() -> dict[str, Any]:
    with open(_SEED_DIR / "fertilizer_reference.json", encoding="utf-8") as fh:
        return json.load(fh)


def _dose_midpoint(rng: list[float]) -> float:
    """Reference doses are [low, high]; plan on the midpoint."""
    if not rng:
        return 0.0
    if len(rng) == 1:
        return float(rng[0])
    return round((float(rng[0]) + float(rng[1])) / 2, 1)


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _window_start(prof: dict[str, Any], today: date) -> date:
    """First plausible sowing date inside the crop's window, never in the past."""
    win = prof["sowing_window"]
    sm, sd = (int(x) for x in win["start"].split("-"))
    start = date(today.year, sm, sd)
    if start < today - timedelta(days=200):
        start = date(today.year + 1, sm, sd)
    return start


async def _schedule_without_doses(
    name: str,
    soil_type: str,
    farm_size_acres: float,
    sowing_date: str | None,
    ref: dict[str, Any],
) -> dict[str, Any]:
    """Timing-only schedule for a crop with no published dose table.

    The KB crop calendars give WHEN to fertilize and the split ratio for every
    crop, but kg/acre tables only exist for the staple field crops. For the rest
    we return the real timing and say the quantities are unavailable — inventing
    a dose is the one thing this tool must never do.
    """
    prof = crop_profiles()[name]
    soil = normalize_soil(soil_type)
    acres = float(farm_size_acres or 1.0)
    today = date.today()

    anchor = _parse_date(sowing_date)
    anchor_note = f"farmer-chosen sowing date {anchor}" if anchor else None
    if anchor is None:
        anchor = max(_window_start(prof, today), today + timedelta(days=5))
        anchor_note = f"default anchor inside the {prof['sowing_window']['label']} window"

    schedule = [
        {
            "date": (anchor + timedelta(days=int(st["das"]))).isoformat(),
            "das": int(st["das"]),
            "stage": st["stage"],
            "inputs": [],
            "stage_cost_bdt": 0,
            "because": st["action"],
        }
        for st in prof["stages"]
        if any(k in st["stage"].lower() for k in ("fertilizer", "urea", "top-dress", "gypsum"))
    ]
    irrigation = [
        {
            "date": (anchor + timedelta(days=int(st["das"]))).isoformat(),
            "das": int(st["das"]),
            "event": st["stage"],
            "action": st["action"],
            "condition": "always",
        }
        for st in prof["stages"]
        if any(k in st["stage"].lower() for k in ("irrigat", "drain", "mulch"))
    ]

    kb_refs = await retriever.search_compact(f"{name} fertilizer application guidance", k=2)

    return {
        "crop": name,
        "soil_type": soil,
        "farm_size_acres": acres,
        "sowing_anchor": anchor.isoformat(),
        "anchor_reason": anchor_note,
        "doses_available": False,
        "seasonal_doses_kg_per_acre": {},
        "fertilizer_schedule": schedule,
        "irrigation_schedule": irrigation,
        "cost_breakdown": [],
        "total_fertilizer_cost_bdt": None,
        "organic_alternatives": [],
        "adjustments_applied": [],
        "weather_rules": ref["weather_rules"],
        "kb_references": kb_refs,
        "source": prof["source"],
        "quantities_note": (
            f"TIMING ONLY — our knowledge base publishes kg/acre dose tables for "
            f"{', '.join(ref['crops'])} but not for {name}. The dates and split "
            f"ratios above come from the {name} crop calendar; the exact "
            f"quantities are NOT in our sources, so none are stated here. Ask your "
            f"local DAE Sub-Assistant Agriculture Officer for the {name} dose, or "
            f"consult BARC FRG-2018 directly."
        ),
        "price_note": (
            "No cost estimate is given because the quantities are unknown — a "
            "costed schedule would require inventing the doses."
        ),
    }


async def build_fertilizer_schedule(
    crop: str,
    soil_type: str,
    farm_size_acres: float,
    sowing_date: str | None = None,
    use_organic: bool = False,
    weather_summary: dict[str, Any] | None = None,
    daily_weather: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return a stage-by-stage fertilizer + irrigation schedule with costs.

    - `soil_type` drives the sandy-soil adjustment (extra MoP, more urea splits).
    - `use_organic` applies the KB cowdung rule (2 t/acre → cut urea & TSP ~20%)
      and surfaces organic alternatives.
    - `daily_weather` (the `daily` list from get_weather) lets the scheduler flag
      urea top-dressings that fall within 48h of forecast heavy rain.
    All doses/prices come from data/seed/fertilizer_reference.json (KB-grounded).
    """
    name = match_crop_name(crop)
    if not name:
        return {"error": f"unknown crop '{crop}'", "known_crops": list(crop_profiles().keys())}

    ref = _fertilizer_reference()
    crop_ref = ref["crops"].get(name)
    if not crop_ref:
        # No published dose table for this crop in our KB. Rather than invent
        # kg figures, return the timing and split ratios the crop calendar DOES
        # document, and say plainly that the quantities are not available.
        return await _schedule_without_doses(name, soil_type, farm_size_acres, sowing_date, ref)

    soil = normalize_soil(soil_type)
    acres = float(farm_size_acres or 1.0)
    prices = ref["prices_bdt_per_kg"]

    # ---- Per-acre doses (midpoint of the KB range), with adjustments ----
    doses = {item: _dose_midpoint(rng) for item, rng in crop_ref["doses_kg_per_acre"].items()}
    adjustments: list[str] = []

    sandy_adj = ref["soil_adjustments"]["sandy"]
    if soil == "sandy" and "MoP" in doses:
        doses["MoP"] = round(doses["MoP"] * sandy_adj["mop_multiplier"], 1)
        adjustments.append(
            f"sandy soil → +25% MoP (now {doses['MoP']} kg/acre) and urea split into "
            f"more, smaller doses to cut leaching ({sandy_adj['source']})"
        )

    organic_lines: list[dict[str, Any]] = []
    if use_organic:
        org = ref["organic_rule"]
        for item in ("Urea", "TSP"):
            if item in doses:
                doses[item] = round(doses[item] * org["urea_tsp_multiplier"], 1)
        cowdung_kg = org["cowdung_kg_per_acre"]
        organic_lines.append(
            {
                "input": "Cowdung / compost",
                "qty_kg_per_acre": cowdung_kg,
                "qty_kg_total": round(cowdung_kg * acres),
                "replaces": "~20% of the urea and TSP",
                "because": org["rule"] + f" ({org['source']})",
            }
        )
        adjustments.append(
            f"organic option → applying {org['cowdung_kg_per_acre']:,} kg/acre cowdung, "
            f"chemical urea & TSP cut ~20% ({org['source']})"
        )

    # ---- Cost of the full-season chemical fertilizer bill ----
    cost_lines: list[dict[str, Any]] = []
    real_price_items: list[str] = []
    for item, per_acre in doses.items():
        pinfo = prices.get(item, {})
        unit_price = float(pinfo.get("price", 0))
        total_kg = round(per_acre * acres, 1)
        line_cost = round(total_kg * unit_price)
        if "REAL" in pinfo.get("source", ""):
            real_price_items.append(item)
        cost_lines.append(
            {
                "input": item,
                "kg_per_acre": per_acre,
                "kg_total": total_kg,
                "price_bdt_per_kg": unit_price,
                "cost_bdt": line_cost,
                "price_source": pinfo.get("source", "unknown"),
            }
        )
    total_fertilizer_cost = round(sum(c["cost_bdt"] for c in cost_lines))

    # ---- Anchor the calendar so each application/irrigation gets a real date ----
    today = date.today()
    anchor = _parse_date(sowing_date)
    anchor_note = f"farmer-chosen sowing date {anchor}" if anchor else None
    if anchor is None:
        anchor = max(_window_start(crop_profiles()[name], today), today + timedelta(days=5))
        anchor_note = (
            f"default anchor inside the {crop_profiles()[name]['sowing_window']['label']} window"
        )

    # Map of forecast rain by ISO date, when the caller passed live daily weather.
    rain_by_date: dict[str, float] = {}
    for d in daily_weather or []:
        if d.get("date") is not None and d.get("rain_mm") is not None:
            rain_by_date[str(d["date"])] = float(d["rain_mm"])

    def _rain_flag(when: date, is_urea: bool) -> str | None:
        """Warn if a urea top-dress falls within 48h of forecast heavy rain."""
        if not is_urea or not rain_by_date:
            return None
        for offset in (0, 1, 2):
            iso = (when + timedelta(days=offset)).isoformat()
            mm = rain_by_date.get(iso)
            if mm is not None and mm >= _HEAVY_RAIN_MM:
                return (
                    f"{mm:.0f} mm rain forecast on {iso} (within 48h) — DELAY this urea "
                    f"top-dress until after the rain; applying now loses 30–40% of the "
                    f"nitrogen to runoff (fertilizer_guide.md weather rule 1)"
                )
        return None

    # ---- Stage-by-stage application schedule ----
    schedule: list[dict[str, Any]] = []
    for app in crop_ref["applications"]:
        when = anchor + timedelta(days=int(app["das"]))
        items = []
        line_cost = 0
        contains_urea = False
        for item, frac in app["items"].items():
            kg_total = round(doses.get(item, 0) * frac * acres, 1)
            if kg_total <= 0:
                continue
            unit_price = float(prices.get(item, {}).get("price", 0))
            item_cost = round(kg_total * unit_price)
            line_cost += item_cost
            if item == "Urea":
                contains_urea = True
            items.append(
                {
                    "input": item,
                    "kg": kg_total,
                    "fraction_of_seasonal_dose": round(frac, 3),
                    "cost_bdt": item_cost,
                }
            )
        entry: dict[str, Any] = {
            "date": when.isoformat(),
            "das": int(app["das"]),
            "stage": app["stage"],
            "inputs": items,
            "stage_cost_bdt": line_cost,
            "because": app.get("note", ""),
        }
        flag = _rain_flag(when, contains_urea)
        if flag:
            entry["weather_alert"] = flag
        schedule.append(entry)

    # ---- Irrigation schedule (dated, condition-tagged) ----
    irrigation: list[dict[str, Any]] = []
    for irr in crop_ref.get("irrigation", []):
        when = anchor + timedelta(days=int(irr["das"]))
        irrigation.append(
            {
                "date": when.isoformat(),
                "das": int(irr["das"]),
                "event": irr["event"],
                "action": irr["action"],
                "condition": irr.get("condition", "always"),
            }
        )

    kb_refs = await retriever.search_compact(f"{name} fertilizer dose urea TSP MoP timing", k=2)

    price_note = (
        "Urea/TSP/DAP/MoP priced at REAL government-fixed dealer rates "
        "(MoA notification Apr-2023); gypsum/zinc/boron/cowdung are market estimates."
        if real_price_items
        else "prices are market estimates"
    )

    return {
        "crop": name,
        "soil_type": soil,
        "farm_size_acres": acres,
        "sowing_anchor": anchor.isoformat(),
        "anchor_reason": anchor_note,
        "seasonal_doses_kg_per_acre": doses,
        "fertilizer_schedule": schedule,
        "irrigation_schedule": irrigation,
        "cost_breakdown": cost_lines,
        "total_fertilizer_cost_bdt": total_fertilizer_cost,
        "organic_alternatives": organic_lines,
        "adjustments_applied": adjustments,
        "weather_rules": ref["weather_rules"],
        "kb_references": kb_refs,
        "source": crop_ref["source"],
        "price_note": price_note,
    }
