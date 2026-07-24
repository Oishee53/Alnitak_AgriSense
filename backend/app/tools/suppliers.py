"""Marketplace / supplier comparison (Tier 2).

Given the crop and farm size, works out how much fertilizer the farmer actually
needs (from the same FRG-2018 dose tables the fertilizer scheduler uses), then
prices that exact basket at every supplier in the catalog and ranks them by
total cost — so the advice is "buy your inputs at X, it's cheapest for *your*
quantities", not a generic list. Deterministic; the LLM repeats these numbers.

The supplier catalog (distances, ratings, per-kg prices) is seeded/mock
(data/seed/suppliers.json) — the brief explicitly allows a seeded catalog. This
is disclosed in every result and in the README's real-vs-mock table.
"""
from __future__ import annotations

from typing import Any

from app.tools.seed_data import (
    fertilizer_reference,
    match_crop_name,
    normalize_soil,
    suppliers,
)

# Map our fertilizer product names → the per-kg price keys in suppliers.json.
_PRODUCT_TO_CATALOG = {
    "Urea": "urea_kg",
    "TSP": "tsp_kg",
    "MoP": "mop_kg",
}


def _mid(rng: Any) -> float:
    """Midpoint of a [low, high] dose range (or the scalar itself)."""
    if isinstance(rng, (list, tuple)) and rng:
        return (float(rng[0]) + float(rng[-1])) / 2
    return float(rng or 0)


def _needs(name: str, acres: float, soil_type: str | None) -> dict[str, float]:
    """Total kg of urea/TSP/MoP for this crop and farm size (FRG midpoints).

    Applies the KB's sandy-soil rule (+25% MoP) so the basket matches what the
    fertilizer scheduler would prescribe.
    """
    ref = fertilizer_reference().get(name) or {}
    doses = ref.get("doses_kg_per_acre") or {}
    if not doses:
        return {}
    sandy = normalize_soil(soil_type) == "sandy"
    needs: dict[str, float] = {}
    for product, catalog_key in _PRODUCT_TO_CATALOG.items():
        per_acre = _mid(doses.get(product))
        if per_acre <= 0:
            continue
        if product == "MoP" and sandy:
            per_acre *= 1.25
        needs[catalog_key] = round(per_acre * float(acres), 1)
    return needs


async def compare_suppliers(
    crop: str,
    farm_size_acres: float,
    soil_type: str | None = None,
) -> dict[str, Any]:
    """Rank input suppliers by the total cost of this farm's fertilizer basket."""
    name = match_crop_name(crop) or crop
    needs = _needs(name, farm_size_acres, soil_type)
    if not needs:
        return {
            "error": f"no kg/acre dose table for '{crop}', so input quantities "
            "can't be sized",
            "crops_with_tables": [
                k for k, v in fertilizer_reference().items()
                if v.get("doses_kg_per_acre")
            ],
        }

    ranked: list[dict[str, Any]] = []
    for sup in suppliers():
        items = sup.get("items", {})
        lines: list[dict[str, Any]] = []
        total = 0
        for catalog_key, qty in needs.items():
            unit_price = items.get(catalog_key)
            if unit_price is None:
                continue
            cost = round(qty * unit_price)
            total += cost
            lines.append(
                {
                    "input": catalog_key.replace("_kg", "").upper(),
                    "qty_kg": qty,
                    "price_bdt_per_kg": unit_price,
                    "line_cost_bdt": cost,
                }
            )
        ranked.append(
            {
                "id": sup["id"],
                "name": sup["name"],
                "distance_km": sup.get("distance_km"),
                "rating": sup.get("rating"),
                "delivery_days": sup.get("delivery_days"),
                "lines": lines,
                "total_input_cost_bdt": total,
            }
        )

    ranked.sort(key=lambda s: s["total_input_cost_bdt"])
    best = ranked[0]
    worst = ranked[-1]
    savings = worst["total_input_cost_bdt"] - best["total_input_cost_bdt"]
    fastest = min(ranked, key=lambda s: s.get("delivery_days", 99))
    top_rated = max(ranked, key=lambda s: s.get("rating", 0))
    total_kg = round(sum(needs.values()), 1)

    because = (
        f"{best['name']} is cheapest for your {total_kg:g} kg fertilizer basket "
        f"at {best['total_input_cost_bdt']:,} BDT"
        + (f" — saves {savings:,} BDT vs {worst['name']}" if savings > 0 else "")
        + f". It delivers in {best['delivery_days']} day(s), rated {best['rating']}, "
        f"{best['distance_km']} km away."
    )
    tradeoffs = []
    if fastest["id"] != best["id"]:
        tradeoffs.append(
            f"{fastest['name']} delivers fastest ({fastest['delivery_days']} day(s))"
        )
    if top_rated["id"] != best["id"]:
        tradeoffs.append(f"{top_rated['name']} is highest-rated ({top_rated['rating']})")

    return {
        "crop": name,
        "farm_size_acres": float(farm_size_acres),
        "needs_kg": needs,
        "suppliers": ranked,
        "best_supplier_id": best["id"],
        "savings_vs_worst_bdt": savings,
        "recommendation": f"Buy from {best['name']}",
        "because": because,
        "tradeoffs": tradeoffs,
        "catalog_source": "seeded/mock (data/seed/suppliers.json — a seeded "
        "catalog is allowed by the brief)",
    }
