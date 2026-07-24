"""Market price intelligence (Tier 2).

Current + recent price history for a crop, a trend read, and a concrete
sell-now / store / wait recommendation with reasoning — factoring in whether the
crop actually keeps in storage. Pure, deterministic logic over seed data; the
LLM repeats these numbers, it never invents them.

Prices are seeded/mock (data/seed/market_prices.json) until a real feed is
wired — this is disclosed in every result (`price_source`) and in the README's
real-vs-mock table.
"""
from __future__ import annotations

from typing import Any

from app.tools.seed_data import (
    crop_economics,
    market_prices,
    match_crop_name,
)

# Crops that keep for weeks/months if stored properly, so "wait for a better
# price" is a real option. Perishables (leafy/juicy vegetables, tubers that rot
# fast) can't wait — a rising price is a reason to sell NOW, before it spoils.
_STORABLE = {
    "T. Aman Rice", "Boro Rice", "Aus Rice", "Maize (Kharif)", "Maize",
    "Wheat", "Mustard", "Jute", "Lentil", "Chickpea", "Mungbean",
    "Groundnut", "Garlic", "Sugarcane",
}


def _is_storable(name: str) -> bool:
    if name in _STORABLE:
        return True
    low = name.lower()
    return any(k in low for k in ("rice", "wheat", "maize", "lentil", "gram",
                                  "pulse", "bean", "mustard", "jute", "nut"))


def _find_price(name: str, raw: str) -> tuple[str | None, dict[str, Any] | None]:
    """Look up a price entry, tolerating name variants.

    Returns (matched_key, entry) or (None, None). Handles: exact key, the raw
    user string, the base name with any "(…)" suffix stripped ("Maize (Kharif)"
    → "Maize"), a rice proxy (Aman has no separate quote — use Boro/Aus rice),
    then a loose substring match.
    """
    prices = market_prices()
    for key in (name, raw):
        if key and key in prices:
            return key, prices[key]
    base = name.split("(")[0].strip()
    if base in prices:
        return base, prices[base]
    low = name.lower()
    if any(k in low for k in ("rice", "paddy", "aman", "dhan")):
        for k in ("Boro Rice", "Aus Rice"):
            if k in prices:
                return k, prices[k]
    for k in prices:
        if base and (base.lower() in k.lower() or k.lower() in base.lower()):
            return k, prices[k]
    return None, None


def _trend(history: list[float], current: float) -> dict[str, Any]:
    """Overall (first→current) and recent (prev→current) % change + direction."""
    series = list(history)
    if not series or series[-1] != current:
        series = series + [current]
    if len(series) < 2:
        return {"direction": "stable", "change_pct_overall": 0.0, "change_pct_recent": 0.0}
    first, prev = series[0], series[-2]
    overall = round((current - first) / first * 100, 1) if first else 0.0
    recent = round((current - prev) / prev * 100, 1) if prev else 0.0
    if recent > 2:
        direction = "rising"
    elif recent < -2:
        direction = "falling"
    else:
        direction = "stable"
    return {
        "direction": direction,
        "change_pct_overall": overall,
        "change_pct_recent": recent,
    }


def _recommendation(direction: str, storable: bool, recent_pct: float) -> tuple[str, str]:
    """(call, because) for the sell/store/wait decision."""
    if direction == "rising":
        if storable:
            return (
                "STORE / WAIT",
                f"prices are rising (+{recent_pct:g}% vs last period) and this crop "
                "stores well — hold a while to capture the climb, if you have dry storage",
            )
        return (
            "SELL SOON",
            f"prices are rising (+{recent_pct:g}%) but this crop is perishable — "
            "sell into the high now rather than risk it spoiling before prices peak",
        )
    if direction == "falling":
        return (
            "SELL NOW",
            f"prices are falling ({recent_pct:g}% vs last period) — sell now, "
            "waiting is likely to fetch less",
        )
    # stable
    if storable:
        return (
            "SELL NOW or STORE",
            "prices are flat — sell now for cash, or store only if you expect the "
            "usual post-harvest seasonal rise and can store without loss",
        )
    return (
        "SELL NOW",
        "prices are flat and the crop is perishable — no gain from holding, sell now",
    )


async def get_market_prices(
    crop: str,
    farm_size_acres: float | None = None,
    expected_yield_per_acre: float | None = None,
) -> dict[str, Any]:
    """Return current price, recent history, trend and a sell/store/wait call.

    If a farm size is known, also estimates gross revenue at the current price
    using the farmer's stated yield (or the reference yield from crop_economics).
    """
    name = match_crop_name(crop) or crop
    key, entry = _find_price(name, crop)
    if not entry:
        return {
            "error": f"no market price on file for '{crop}'",
            "known_markets": sorted(market_prices().keys()),
        }

    current = float(entry["current"])
    unit = entry.get("unit", "maund")
    history = [float(x) for x in entry.get("history", [])]
    trend = _trend(history, current)
    storable = _is_storable(name)
    call, because = _recommendation(trend["direction"], storable, trend["change_pct_recent"])

    result: dict[str, Any] = {
        "crop": name,
        "market_key": key,
        "unit": unit,
        "current_price_bdt": current,
        "history": history,
        "trend": trend,
        "storable": storable,
        "recommendation": call,
        "because": because,
        "price_source": "seeded/mock (data/seed/market_prices.json — not a live feed)",
    }
    if key != name:
        result["proxy_note"] = f"using '{key}' as a price proxy for '{name}'"

    # Gross revenue at the current price, if we can size it.
    if farm_size_acres:
        econ = crop_economics().get(name) or {}
        yld = expected_yield_per_acre or econ.get("yield_per_acre")
        if yld:
            total_units = round(float(yld) * float(farm_size_acres), 1)
            result["revenue_estimate"] = {
                "yield_per_acre": float(yld),
                "farm_size_acres": float(farm_size_acres),
                "total_units": total_units,
                "unit": unit,
                "gross_revenue_bdt": round(total_units * current),
                "because": (
                    f"{total_units:g} {unit} × {current:g} BDT at today's price "
                    f"({'your stated yield' if expected_yield_per_acre else 'reference yield'})"
                ),
            }
    return result
