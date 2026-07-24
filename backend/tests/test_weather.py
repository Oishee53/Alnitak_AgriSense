"""Smoke test for the live weather tool.

Marked `network` because it hits the real Open-Meteo API. Run explicitly:
    pytest -m network
Skip in offline/CI by default via the marker in pytest config (add if desired).
"""
from __future__ import annotations

import pytest

from app.tools.weather import get_weather


@pytest.mark.asyncio
@pytest.mark.network
async def test_get_weather_returns_real_values():
    data = await get_weather(location="Rangpur, Bangladesh", days=3)
    assert data["summary"]["source"] == "open-meteo"
    assert len(data["daily"]) >= 1
    assert data["latitude"] and data["longitude"]
    # rainfall total is a real number (>= 0), not invented
    assert data["summary"]["total_rain_mm"] >= 0
