"""Scenario simulation (Tier 1).

"What if rainfall drops 30%?" / "What if my budget is cut 40%?" — return a
REVISED plan with changed numbers, not a generic answer. Re-runs the finance /
crop / plan tools with perturbed inputs and diffs the result.
"""
from __future__ import annotations

from typing import Any


async def simulate(
    base_plan: dict[str, Any],
    change: dict[str, Any],
) -> dict[str, Any]:
    """Apply a what-if change and return {before, after, deltas}.

    `change` examples:
        {"rainfall_pct": -30}
        {"budget_pct": -40}
        {"price_bdt_per_unit": 1100}

    TODO: clone base inputs, apply the perturbation, re-invoke finance/crop tools,
    and compute the deltas so the farmer sees exactly what moved.
    """
    raise NotImplementedError
