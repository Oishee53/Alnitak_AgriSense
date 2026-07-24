"""Market price intelligence (Tier 2).

Current + historical prices, plus a sell-now / store / wait recommendation with
reasoning. Prices are seeded/mock (data/seed/market_prices.json) until a real
feed is wired — keep that honest in the README's real-vs-mock table.
"""
from __future__ import annotations

from typing import Any


async def get_market_prices(crop: str, market: str | None = None) -> dict[str, Any]:
    """Return current + historical prices and a sell/store/wait call.

    TODO: load seeded prices; compute trend; return recommendation + `because`.
    """
    raise NotImplementedError
