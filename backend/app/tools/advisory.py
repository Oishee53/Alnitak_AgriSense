"""Proactive, weather-triggered advice (Tier 1).

The difference between a static plan and an *agent* that adapts: this tool watches
the LIVE forecast against the crop's upcoming plan actions and emits dated
adjustments — e.g. "heavy rain in 3 days, delay the urea top-dress by 3 days to
cut nitrogen runoff" — grounded in the KB weather-timing rules (BARC FRG-2018).

It is deliberately self-contained: given a crop + location it fetches the real
forecast (Open-Meteo) and builds the dated plan itself, so the agent can call it
in one step. Every alert names the forecast numbers and plan stage it rests on,
so the reasoning is inspectable in the trace.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from app.rag import retriever
from app.tools.season_plan import build_season_plan
from app.tools.seed_data import match_crop_name
from app.tools.weather import get_weather

# KB-grounded threshold: BARC FRG-2018 calls >20 mm/day "heavy" and warns that
# top-dressed urea within 48 h of it loses 30–40% of its nitrogen to runoff.
HEAVY_RAIN_MM = 20.0
WET_DAY_MM = 10.0        # a day wet enough that irrigation is redundant
DRY_DAY_MM = 2.0         # effectively no rain
HOT_TMAX_C = 33.0        # heat that stresses water-sensitive stages


def _parse(d: str) -> date | None:
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _classify(stage: str, action: str) -> str | None:
    """Map a plan step to the kind of weather sensitivity it has."""
    s = f"{stage} {action}".lower()
    if "urea" in s or "nitrogen" in s:
        return "nitrogen"
    if "irrigation" in s or "irrigate" in s:
        return "irrigation_stop" if "stop" in s else "irrigation"
    if "harvest" in s or "drain" in s:
        return "harvest"
    if "pest" in s or "disease" in s or "spray" in s or "blight" in s or "borer" in s:
        return "spray"
    if "transplant" in s or "sowing" in s or "planting" in s or "sow " in s:
        return "establishment"
    return None


def _window(fmap: dict[str, dict], d0: date, back: int = 1, fwd: int = 2) -> dict[str, Any]:
    """Aggregate forecast over [d0-back, d0+fwd] for the days we actually have."""
    rains, tmaxes, hits = [], [], []
    for off in range(-back, fwd + 1):
        row = fmap.get((d0 + timedelta(days=off)).isoformat())
        if not row:
            continue
        if row.get("rain_mm") is not None:
            rains.append(row["rain_mm"])
        if row.get("t_max") is not None:
            tmaxes.append(row["t_max"])
        hits.append(row)
    return {
        "days": len(hits),
        "total_rain_mm": round(sum(rains), 1) if rains else None,
        "max_rain_mm": round(max(rains), 1) if rains else None,
        "avg_t_max": round(sum(tmaxes) / len(tmaxes), 1) if tmaxes else None,
    }


def _next_dry_date(fmap: dict[str, dict], start: date, horizon_end: date) -> date | None:
    """First forecast day on/after `start` that is dry enough to top-dress urea."""
    d = start
    while d <= horizon_end:
        row = fmap.get(d.isoformat())
        if row and (row.get("rain_mm") or 0) < WET_DAY_MM:
            return d
        d += timedelta(days=1)
    return None


async def weather_advisory(
    crop: str,
    location: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    sowing_date: str | None = None,
    soil_type: str | None = None,
    water_availability: str | None = None,
    days: int = 16,
    weather: dict[str, Any] | None = None,
    season_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Cross-check the live forecast against the crop's upcoming plan actions and
    return dated, weather-triggered adjustments.

    Returns {crop, location, forecast_window, plan_actions_in_window, alerts,
    kb_references, source}. `alerts` each carry the triggering forecast numbers,
    the affected plan stage, a recommendation, and a `because`.
    """
    name = match_crop_name(crop) or crop

    # --- live forecast (reuse a passed-in result, else fetch real values) ---
    if not (weather and weather.get("daily")):
        if location is None and latitude is None:
            return {"error": "need a location (or latitude/longitude) to fetch the forecast"}
        weather = await get_weather(
            location=location or "", latitude=latitude, longitude=longitude, days=days
        )
    daily = weather.get("daily", [])
    if not daily:
        return {"error": "no forecast data available", "location": weather.get("location")}

    fmap = {row["date"]: row for row in daily if row.get("date")}
    fdates = sorted(d for d in (_parse(x) for x in fmap) if d)
    horizon_start, horizon_end = fdates[0], fdates[-1]

    # --- dated plan (reuse a passed-in plan, else build it) ---
    if not (season_plan and season_plan.get("stages")):
        season_plan = await build_season_plan(
            crop=name, sowing_date=sowing_date, soil_type=soil_type
        )
    if "error" in season_plan:
        return {"error": f"could not build plan for '{crop}': {season_plan['error']}"}
    stages = season_plan.get("stages", [])

    # --- stages that fall inside the forecast horizon ---
    actions_in_window: list[dict[str, Any]] = []
    for st in stages:
        d = _parse(st.get("date", ""))
        if d and horizon_start <= d <= horizon_end:
            actions_in_window.append({"date": st["date"], "stage": st["stage"], "action": st["action"]})

    alerts: list[dict[str, Any]] = []

    def add(kind, severity, when, stage, trigger, recommendation, because):
        alerts.append({
            "date": when, "kind": kind, "severity": severity, "stage": stage,
            "trigger": trigger, "recommendation": recommendation, "because": because,
        })

    # --- per-stage, weather-triggered adjustments ---
    for st in stages:
        d = _parse(st.get("date", ""))
        if not d or not (horizon_start <= d <= horizon_end):
            continue
        kind = _classify(st.get("stage", ""), st.get("action", ""))
        if not kind:
            continue
        w = _window(fmap, d)
        max_rain = w["max_rain_mm"] or 0
        total_rain = w["total_rain_mm"] or 0
        tmax = w["avg_t_max"]

        if kind == "nitrogen" and max_rain >= HEAVY_RAIN_MM:
            dry = _next_dry_date(fmap, d + timedelta(days=1), horizon_end)
            delay = (dry - d).days if dry else None
            rec = (
                f"Delay this urea top-dress to {dry.isoformat()} (~{delay} day"
                f"{'s' if delay != 1 else ''} later)" if dry
                else "Hold this urea top-dress until the wet spell passes"
            )
            add("nitrogen-timing", "high", st["date"], st["stage"],
                f"{max_rain} mm rain forecast around {st['date']} (>{HEAVY_RAIN_MM:g} mm = heavy)",
                rec,
                "top-dressed urea within 48 h of heavy rain loses 30–40% of its "
                "nitrogen to runoff (BARC FRG-2018 weather-timing rule)")
        elif kind == "irrigation" and total_rain >= WET_DAY_MM:
            add("irrigation", "advice", st["date"], st["stage"],
                f"{total_rain} mm rain forecast around {st['date']}",
                "Skip or delay this irrigation — the forecast rain covers the crop's need; save the diesel/electricity cost",
                f"{total_rain} mm over this window meets the stage's water need without irrigating")
        elif kind == "irrigation" and total_rain < DRY_DAY_MM and (tmax or 0) >= HOT_TMAX_C:
            add("irrigation", "warning", st["date"], st["stage"],
                f"only {total_rain} mm rain and {tmax}°C forecast around {st['date']}",
                "Irrigate on schedule — do not skip; the window is hot and dry",
                "a hot, rain-free window at this stage risks water stress and yield loss")
        elif kind == "spray" and max_rain >= WET_DAY_MM:
            add("spray-window", "advice", st["date"], st["stage"],
                f"{max_rain} mm rain forecast around {st['date']}",
                "Spray in a dry gap before the rain (or wait until after) — rain within a few hours washes off contact pesticide/fungicide",
                "rainfall soon after spraying removes the active ingredient before it acts")
        elif kind == "harvest" and max_rain >= HEAVY_RAIN_MM:
            add("harvest", "high", st["date"], st["stage"],
                f"{max_rain} mm rain forecast around {st['date']}",
                "Harvest before the rain if the crop is ready, or ensure field drainage",
                "heavy rain at harvest causes lodging, grain shattering and wet-grain quality loss")
        elif kind == "establishment" and max_rain >= HEAVY_RAIN_MM:
            add("establishment", "warning", st["date"], st["stage"],
                f"{max_rain} mm rain forecast around {st['date']}",
                "Ensure drainage before transplanting/sowing; delay a day or two if the field will flood",
                "young seedlings/seed can be washed out or waterlogged by heavy rain right after establishment")

    # --- season-level watchpoints from the raw forecast (independent of stages) ---
    heavy = [(row["date"], row["rain_mm"]) for row in daily
             if (row.get("rain_mm") or 0) >= HEAVY_RAIN_MM]
    if heavy:
        d0, mm = heavy[0]
        hd = _parse(d0)
        # If a plan-specific alert already flags this heavy-rain day, don't emit a
        # duplicate generic card. For a nitrogen alert (which only covers the urea
        # angle) fold in the missing waterlogging note; establishment/harvest
        # alerts already advise drainage, so just stay silent.
        covering = next(
            (a for a in alerts
             if a["kind"] in ("nitrogen-timing", "establishment", "harvest")
             and hd and (pd := _parse(a["date"])) and abs((pd - hd).days) <= 2),
            None,
        )
        if covering is None:
            add("heavy-rain", "warning", d0, None,
                f"{mm} mm forecast on {d0}" + (f" (+{len(heavy)-1} more heavy day(s))" if len(heavy) > 1 else ""),
                "Do not top-dress urea within 48 h of this; check field bunds and drainage",
                "heavy rain drives nitrogen runoff and waterlogging (BARC FRG-2018)")
        elif covering["kind"] == "nitrogen-timing":
            covering["recommendation"] = (
                covering["recommendation"].rstrip(".")
                + ". Also check field bunds and drainage against waterlogging"
            )

    summ = weather.get("summary", {})
    total = summ.get("total_rain_mm")
    if total is not None and total < 5 and (summ.get("avg_t_max") or 0) >= HOT_TMAX_C:
        add("dry-spell", "warning", horizon_start.isoformat(), None,
            f"only {total} mm rain over {len(fdates)} days, avg {summ.get('avg_t_max')}°C",
            "Line up irrigation for water-sensitive stages; apply urea only after irrigating",
            "a hot, rain-free spell stresses the crop and wastes urea applied to dry soil")

    alerts.sort(key=lambda a: a["date"])

    kb_refs = await retriever.search_compact(
        f"{name} fertilizer urea timing weather rain irrigation", k=2
    )

    return {
        "crop": name,
        "location": weather.get("location"),
        "forecast_window": {
            "start": horizon_start.isoformat(),
            "end": horizon_end.isoformat(),
            "days": len(fdates),
            "total_rain_mm": summ.get("total_rain_mm"),
            "max_daily_rain_mm": max((row.get("rain_mm") or 0 for row in daily), default=0),
            "avg_t_max": summ.get("avg_t_max"),
            "source": "open-meteo",
        },
        "plan_actions_in_window": actions_in_window,
        "alerts": alerts,
        "kb_references": kb_refs,
        "source": "open-meteo forecast + BARC FRG-2018 weather-timing rules",
        "note": (
            "No plan actions fall within the forecast window; showing season-level "
            "forecast watchpoints only."
            if not actions_in_window else
            f"{len(alerts)} weather-triggered item(s) against {len(actions_in_window)} "
            "upcoming plan action(s)."
        ),
    }
