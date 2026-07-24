"""Market price intelligence tests (Tier 2).

Deterministic over the seed prices — no network. Pin the trend read, the
sell/store/wait logic (storable vs perishable), the rice price proxy, and the
gross-revenue estimate.
"""
from __future__ import annotations

import pytest

from app.tools.market import get_market_prices


@pytest.mark.asyncio
async def test_falling_perishable_says_sell_now():
    # Potato history [820,780,740,700] → falling; potato is perishable.
    r = await get_market_prices("Potato")
    assert r["trend"]["direction"] == "falling"
    assert r["recommendation"] == "SELL NOW"
    assert r["storable"] is False
    assert r["current_price_bdt"] == 700


@pytest.mark.asyncio
async def test_rising_storable_says_store_wait():
    # Mungbean history [4200,4300,4400,4500] → rising; a pulse, so storable.
    r = await get_market_prices("Mungbean")
    assert r["trend"]["direction"] == "rising"
    assert r["storable"] is True
    assert r["recommendation"] == "STORE / WAIT"


@pytest.mark.asyncio
async def test_rice_uses_boro_proxy_and_notes_it():
    # T. Aman Rice has no separate quote — must proxy to Boro/Aus rice.
    r = await get_market_prices("T. Aman Rice")
    assert "error" not in r
    assert r["market_key"] in {"Boro Rice", "Aus Rice"}
    assert "proxy" in r.get("proxy_note", "").lower()


@pytest.mark.asyncio
async def test_revenue_estimate_uses_reference_yield():
    # 2 acres × reference yield × current price.
    r = await get_market_prices("Potato", farm_size_acres=2)
    rev = r["revenue_estimate"]
    assert rev["farm_size_acres"] == 2
    expected = round(rev["total_units"] * r["current_price_bdt"])
    assert rev["gross_revenue_bdt"] == expected


@pytest.mark.asyncio
async def test_price_source_is_disclosed_as_mock():
    r = await get_market_prices("Wheat")
    assert "mock" in r["price_source"].lower() or "seed" in r["price_source"].lower()


@pytest.mark.asyncio
async def test_unknown_crop_returns_error_not_crash():
    r = await get_market_prices("Dragonfruit")
    assert "error" in r
    assert r["known_markets"]
