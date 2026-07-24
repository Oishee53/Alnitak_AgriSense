"""Proactive weather-advisory tests (Tier 1).

All tests inject a synthetic forecast + season plan, so they are deterministic
and need no network. They pin the flagship behaviours: the nitrogen-timing
alert before heavy rain, the delay-to-next-dry-day recommendation, the
duplicate-card suppression, and the season-level fallback warning.
"""
from __future__ import annotations

import pytest

from app.tools.advisory import weather_advisory


def _forecast(rains: dict[str, float]) -> dict:
    """Synthetic Open-Meteo-shaped weather for early Aug 2026."""
    days = [f"2026-08-{d:02d}" for d in range(1, 11)]
    daily = [
        {"date": d, "t_max": 31.0, "t_min": 25.0,
         "rain_mm": rains.get(d, 0.0), "precip_prob": 60}
        for d in days
    ]
    vals = [x["rain_mm"] for x in daily]
    return {
        "location": "Testpur, Bangladesh",
        "daily": daily,
        "summary": {
            "total_rain_mm": round(sum(vals), 1),
            "avg_t_max": 31.0,
            "rain_days": sum(1 for v in vals if v > 1),
            "source": "open-meteo",
        },
    }


def _plan(stages: list[tuple[str, str, str]]) -> dict:
    return {
        "crop": "T. Aman Rice",
        "stages": [{"date": d, "stage": s, "action": a} for d, s, a in stages],
    }


@pytest.mark.asyncio
async def test_nitrogen_alert_fires_and_deduplicates():
    # Heavy rain (25 mm) on the same day as the scheduled urea top-dress.
    weather = _forecast({"2026-08-05": 25.0, "2026-08-06": 15.0})
    plan = _plan([("2026-08-05", "Urea top-dress 1", "1/3 urea at tillering")])
    r = await weather_advisory(crop="T. Aman Rice", weather=weather, season_plan=plan)

    kinds = [a["kind"] for a in r["alerts"]]
    assert kinds.count("nitrogen-timing") == 1
    # Dedupe: no separate generic heavy-rain card for the same covered day...
    assert "heavy-rain" not in kinds
    # ...and its waterlogging note is folded into the surviving alert.
    nitro = next(a for a in r["alerts"] if a["kind"] == "nitrogen-timing")
    assert "drainage" in nitro["recommendation"]
    assert nitro["severity"] == "high"


@pytest.mark.asyncio
async def test_nitrogen_alert_recommends_next_dry_day():
    # Heavy rain 08-05, still wet 08-06, dry from 08-07 → delay to 08-07.
    weather = _forecast({"2026-08-05": 25.0, "2026-08-06": 15.0})
    plan = _plan([("2026-08-05", "Urea top-dress 1", "1/3 urea at tillering")])
    r = await weather_advisory(crop="T. Aman Rice", weather=weather, season_plan=plan)
    nitro = next(a for a in r["alerts"] if a["kind"] == "nitrogen-timing")
    assert "2026-08-07" in nitro["recommendation"]


@pytest.mark.asyncio
async def test_generic_heavy_rain_warning_when_no_stage_is_near():
    # Heavy rain but every plan action is outside the forecast window:
    # the season-level warning must still appear (not suppressed).
    weather = _forecast({"2026-08-05": 25.0})
    plan = _plan([("2026-09-20", "Urea top-dress 2", "1/3 urea at PI")])
    r = await weather_advisory(crop="T. Aman Rice", weather=weather, season_plan=plan)
    kinds = [a["kind"] for a in r["alerts"]]
    assert "heavy-rain" in kinds
    assert "nitrogen-timing" not in kinds


@pytest.mark.asyncio
async def test_rain_covered_irrigation_is_flagged_skippable():
    # ≥10 mm around a scheduled irrigation → advise skipping it.
    weather = _forecast({"2026-08-01": 4.0, "2026-08-02": 6.0, "2026-08-03": 5.0})
    plan = _plan([("2026-08-02", "Irrigation 1", "Light irrigation at tillering")])
    r = await weather_advisory(crop="T. Aman Rice", weather=weather, season_plan=plan)
    irr = [a for a in r["alerts"] if a["kind"] == "irrigation"]
    assert len(irr) == 1
    assert "Skip or delay" in irr[0]["recommendation"]
