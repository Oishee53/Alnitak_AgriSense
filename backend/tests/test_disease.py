"""Plant disease detection tests (Tier 2).

The vision call is mocked (a fake LLM returns a canned diagnosis), so these are
deterministic and offline. They pin the KB grounding: a recognised condition
must attach the KB treatment/prevention/cost, an unknown one falls back to the
model's advice (flagged), and non-plant / failure paths degrade gracefully.
"""
from __future__ import annotations

import pytest

from app.agent.llm import LLMClient
from app.tools import disease


class _FakeLLM(LLMClient):
    def __init__(self, payload):
        self._payload = payload  # no super().__init__ — never touches OpenAI

    async def vision_json(self, system, user, image_data_url):
        return self._payload


@pytest.mark.asyncio
async def test_known_disease_is_kb_grounded():
    fake = _FakeLLM(
        {
            "is_plant": True,
            "crop": "rice",
            "condition": "disease",
            "name": "bacterial leaf blight",
            "confidence": "high",
            "visible_symptoms": ["yellow wavy leaf edges"],
            "severity": "moderate",
            "reasoning": "wavy yellow lesions after a storm",
            "advice": "drain the field",
        }
    )
    r = await disease.detect_disease("data:image/jpeg;base64,x", crop="rice", llm=fake)
    assert r["kb_grounded"] is True
    assert r["kb_name"]  # matched a KB entry
    assert r["treatment"]  # KB treatment, not the model's "drain the field"
    assert "prevention" in r
    assert r["crop"] == "T. Aman Rice"  # normalised


@pytest.mark.asyncio
async def test_unknown_condition_falls_back_to_model_advice():
    fake = _FakeLLM(
        {
            "is_plant": True,
            "crop": "rice",
            "condition": "disease",
            "name": "some rare mystery blight not in our KB",
            "confidence": "low",
            "visible_symptoms": ["odd purple streaks"],
            "advice": "isolate the plant and monitor",
        }
    )
    r = await disease.detect_disease("data:image/jpeg;base64,x", crop="rice", llm=fake)
    assert r["kb_grounded"] is False
    assert r["treatment"] == "isolate the plant and monitor"


@pytest.mark.asyncio
async def test_non_plant_image_is_handled():
    fake = _FakeLLM({"is_plant": False})
    r = await disease.detect_disease("data:image/jpeg;base64,x", llm=fake)
    assert r["is_plant"] is False
    assert "message" in r


@pytest.mark.asyncio
async def test_vision_failure_returns_friendly_error():
    fake = _FakeLLM({})  # vision call failed / empty
    r = await disease.detect_disease("data:image/jpeg;base64,x", llm=fake)
    assert "error" in r


@pytest.mark.asyncio
async def test_result_always_carries_disclaimer():
    fake = _FakeLLM(
        {"is_plant": True, "crop": "potato", "condition": "healthy", "name": "",
         "confidence": "high", "visible_symptoms": []}
    )
    r = await disease.detect_disease("data:image/jpeg;base64,x", llm=fake)
    assert "extension officer" in r["disclaimer"].lower()
