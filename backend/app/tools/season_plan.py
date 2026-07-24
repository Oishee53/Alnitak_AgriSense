"""Season plan tool (Tier-0 #4).

Produces a DATED calendar from land preparation to harvest for the chosen crop,
anchored on a sowing date inside the crop's window. Stage offsets come from the
seed profiles (compiled from BRRI/BARC/DAE calendars); KB citations attached.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from app.rag import retriever
from app.tools.seed_data import crop_profiles, match_crop_name, normalize_soil


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _window_dates(window: dict[str, str], today: date) -> tuple[date, date]:
    """Resolve the crop's MM-DD window to concrete dates >= today (roll to next
    year if this year's window already passed)."""
    sm, sd = (int(x) for x in window["start"].split("-"))
    em, ed = (int(x) for x in window["end"].split("-"))
    start = date(today.year, sm, sd)
    end = date(today.year, em, ed)
    if end < start:  # window crosses new year (e.g. Boro Jan-Feb)
        end = date(today.year + 1, em, ed)
    if end < today:  # missed this year entirely
        start, end = date(today.year + 1, sm, sd), date(
            today.year + 1 + (1 if em < sm else 0), em, ed
        )
    return start, end


async def build_season_plan(
    crop: str,
    sowing_date: str | None = None,
    soil_type: str | None = None,
) -> dict[str, Any]:
    """Return a dated season calendar with per-stage reasoning."""
    name = match_crop_name(crop)
    if not name:
        return {
            "error": f"unknown crop '{crop}'",
            "known_crops": list(crop_profiles().keys()),
        }
    prof = crop_profiles()[name]
    today = date.today()

    win_start, win_end = _window_dates(prof["sowing_window"], today)
    anchor = _parse_date(sowing_date)
    anchor_note = f"farmer-chosen sowing date {anchor}" if anchor else None
    if anchor is None:
        # Default: window start, but never in the past; if we're inside the
        # window, give ~5 days of prep lead time.
        anchor = max(win_start, today + timedelta(days=5))
        if anchor > win_end:
            anchor = win_start  # next-year window start
        anchor_note = f"default anchor inside the {prof['sowing_window']['label']} window"

    in_window = win_start <= anchor <= win_end
    soil = normalize_soil(soil_type) if soil_type else None

    stages = []
    for st in prof["stages"]:
        d = anchor + timedelta(days=st["das"])
        because = f"{st['das']:+d} days from sowing/transplanting per {prof['source']}"
        stages.append(
            {
                "date": d.isoformat(),
                "stage": st["stage"],
                "action": st["action"],
                "because": because,
            }
        )

    kb_refs = await retriever.search_compact(f"{name} crop calendar sowing window stages", k=2)

    warnings = []
    if not in_window:
        warnings.append(
            f"Chosen sowing date {anchor} is OUTSIDE the recommended window "
            f"({win_start} to {win_end}) — expect yield loss; consider a short-duration variety."
        )
    if soil == "sandy" and prof["soil"].get("sandy", 1) < 0.5:
        warnings.append(
            f"{name} is poorly suited to sandy soil (suitability {prof['soil']['sandy']}); "
            "expect higher irrigation/nitrogen losses."
        )

    return {
        "crop": name,
        "sowing_window": {
            "start": win_start.isoformat(),
            "end": win_end.isoformat(),
            "label": prof["sowing_window"]["label"],
        },
        "anchor_date": anchor.isoformat(),
        "anchor_reason": anchor_note,
        "duration_days": prof["duration_days"],
        "expected_harvest": (anchor + timedelta(days=prof["duration_days"])).isoformat(),
        "stages": stages,
        "warnings": warnings,
        "kb_references": kb_refs,
        "source": prof["source"],
    }
