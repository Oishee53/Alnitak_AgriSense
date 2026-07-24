"""Financial projection tool (Tier-0 #5).

Itemized cost breakdown + expected yield, revenue, net profit, ROI, break-even.
Pure arithmetic (no LLM): deterministic, inspectable, and unit-tested — change
an input and every derived number changes consistently. Reference costs/yields
come from seed data compiled from public extension figures; prices are seeded
(mock) unless the caller passes one.
"""
from __future__ import annotations

from typing import Any

from app.tools.seed_data import (
    crop_economics,
    market_prices,
    match_crop_name,
)


async def compute_financials(
    crop: str,
    farm_size_acres: float,
    inputs: dict[str, Any] | None = None,
    expected_price_bdt_per_unit: float | None = None,
    expected_yield_per_acre: float | None = None,
) -> dict[str, Any]:
    """Return an itemized, internally-consistent financial projection.

    `inputs` (optional) overrides the default cost lines:
        {"seed": {"qty": 20, "unit_cost": 60}, ...}  → total = qty * unit_cost
    Quantities in `inputs` are treated as absolute (already sized to the farm).
    Without `inputs`, per-acre reference costs are scaled by farm_size_acres.
    """
    assumptions: list[str] = []
    name = match_crop_name(crop) or crop
    econ = crop_economics().get(name)

    # ---- Cost lines ----
    costs: list[dict[str, Any]] = []
    if inputs:
        for item, spec in inputs.items():
            qty = float(spec.get("qty", 0))
            unit_cost = float(spec.get("unit_cost", 0))
            costs.append(
                {
                    "item": str(item).capitalize(),
                    "qty": qty,
                    "unit_cost": unit_cost,
                    "total": round(qty * unit_cost, 2),
                }
            )
        assumptions.append("cost lines supplied by caller (absolute quantities)")
    elif econ:
        for item, per_acre in econ["costs_per_acre"].items():
            costs.append(
                {
                    "item": item,
                    "qty": round(farm_size_acres, 2),
                    "unit_cost": per_acre,
                    "total": round(per_acre * farm_size_acres, 2),
                }
            )
        assumptions.append(
            f"per-acre reference costs for {name} from seed data (compiled from "
            "public DAE/BARI extension figures), scaled by farm size"
        )
    else:
        return {
            "error": f"no cost reference for crop '{crop}' and no inputs given",
            "known_crops": list(crop_economics().keys()),
        }

    total_cost = round(sum(c["total"] for c in costs), 2)

    # ---- Yield ----
    unit = "maund"
    yield_pa = expected_yield_per_acre or (econ["yield_per_acre"] if econ else 0)
    if expected_yield_per_acre:
        assumptions.append(f"caller-specified yield {expected_yield_per_acre} {unit}/acre")
    elif econ:
        assumptions.append(
            f"reference yield {yield_pa} {unit}/acre for {name} (public extension figures)"
        )
    expected_yield = round(yield_pa * farm_size_acres, 1)

    # ---- Price ----
    price = expected_price_bdt_per_unit
    if price is None:
        mp = market_prices().get(name.split(" (")[0])
        price = (mp or {}).get("current") or (econ.get("price_bdt_per_unit") if econ else 0)
        assumptions.append(
            f"price {price} BDT/{unit} from seeded market data (MOCK — replace with live feed)"
        )
    else:
        assumptions.append(f"caller-specified price {price} BDT/{unit}")

    # ---- Derived metrics (all traceable to the numbers above) ----
    revenue = round(expected_yield * price, 2)
    net_profit = round(revenue - total_cost, 2)
    roi = round(net_profit / total_cost, 3) if total_cost else None
    break_even_price = round(total_cost / expected_yield, 2) if expected_yield else None
    break_even_yield = round(total_cost / price, 1) if price else None

    return {
        "crop": name,
        "farm_size_acres": farm_size_acres,
        "costs": costs,
        "total_cost_bdt": total_cost,
        "expected_yield_unit": unit,
        "expected_yield": expected_yield,
        "price_bdt_per_unit": price,
        "revenue_bdt": revenue,
        "net_profit_bdt": net_profit,
        "roi": roi,
        "break_even_price_bdt_per_unit": break_even_price,
        "break_even_yield": break_even_yield,
        "assumptions": assumptions,
    }
