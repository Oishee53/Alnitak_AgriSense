"""Guards against hallucinated farm-profile intake.

Two failure modes reported from manual testing:
  - "small budget" -> the model recorded budget_bdt=15000, a number the
    farmer never gave.
  - a vague soil description -> the model recorded a specific soil_type
    (e.g. "loam") the farmer never confirmed.

Both are fixed the same way: the ORIGINAL FARMER MESSAGE, not the model's
claimed extraction, is the source of truth for whether a number or a soil
texture was actually stated. If the message can't support it, the value is
rejected and the field stays in missing_fields() so the agent asks again for
a specific figure / one of the four soil types — instead of trusting a guess.
"""
from __future__ import annotations

import pytest

from app.agent.orchestrator import (
    Orchestrator,
    _canonical_soil_type,
    _message_has_number,
    _validate_field,
)
from app.memory.store import SessionState


# --------------------------------------------------------------------------
# _message_has_number — the numeric-signal backstop
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "message,expected",
    [
        ("small budget", False),
        ("not much land", False),
        ("enough money for now", False),
        ("", False),
        ("my budget is 15000 BDT", True),
        ("15k", True),
        ("1 lakh", True),
        ("২০০০০ টাকা", True),  # Bengali digits
        ("five acres", True),  # spelled-out number
        ("দুই বিঘা জমি", True),  # Bangla spelled-out number (দুই = two)
        ("I have 2 bigha", True),
    ],
)
def test_message_has_number(message, expected):
    assert _message_has_number(message) is expected


# --------------------------------------------------------------------------
# _canonical_soil_type — strict mapping, no default fallback
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "text,expected",
    [
        ("sandy", "sandy"),
        ("my soil is quite sandy", "sandy"),
        ("loamy soil", "loam"),
        ("দোআঁশ মাটি", "loam"),
        ("clay-ish near the pond", "clay"),
        ("বেলে মাটি", "sandy"),
        ("silt from the river", "silt"),
        ("not sure", None),
        ("good soil", None),
        ("normal soil, nothing special", None),
        ("", None),
    ],
)
def test_canonical_soil_type(text, expected):
    assert _canonical_soil_type(text) == expected


# --------------------------------------------------------------------------
# _validate_field — the shared guard used by all three intake paths
# --------------------------------------------------------------------------
def test_validate_field_rejects_number_with_no_signal_in_message():
    """The exact reported bug: a fabricated 15000 for 'small budget'."""
    clean, reason = _validate_field("budget_bdt", 15000, "small budget")
    assert clean is None
    assert reason is not None


def test_validate_field_accepts_number_the_message_actually_gives():
    clean, reason = _validate_field("budget_bdt", 15000, "my budget is 15000 BDT")
    assert clean == 15000.0
    assert reason is None


def test_validate_field_rejects_farm_size_with_no_signal():
    clean, reason = _validate_field("farm_size_acres", 3, "I don't have much land")
    assert clean is None
    assert reason is not None


def test_validate_field_accepts_farm_size_the_message_gives():
    clean, reason = _validate_field("farm_size_acres", 2, "I have 2 acres")
    assert clean == 2.0
    assert reason is None


def test_validate_field_rejects_soil_the_message_does_not_support():
    """The model can echo a plausible value ('loam') for a vague message
    ('good soil') — validation must catch this by checking the MESSAGE, not
    just whether the model's returned string happens to be a known texture."""
    clean, reason = _validate_field("soil_type", "loam", "my soil is good, not sure what type")
    assert clean is None
    assert reason is not None


def test_validate_field_accepts_soil_the_message_states():
    clean, reason = _validate_field("soil_type", "sandy", "the field is quite sandy")
    assert clean == "sandy"
    assert reason is None


def test_validate_field_soil_self_corrects_from_the_message():
    """If the model's value disagrees with the message, the message wins."""
    clean, reason = _validate_field("soil_type", "clay", "definitely sandy soil here")
    assert clean == "sandy"
    assert reason is None


def test_validate_field_passes_through_non_validated_fields():
    clean, reason = _validate_field("location", "Rangpur", "I'm near Rangpur")
    assert clean == "Rangpur"
    assert reason is None


# --------------------------------------------------------------------------
# Orchestrator._apply_profile_update — the tool-call path
# --------------------------------------------------------------------------
def test_apply_profile_update_rejects_fabricated_budget_keeps_it_missing():
    orch = Orchestrator()
    state = SessionState(id="t-budget")
    result = orch._apply_profile_update(
        state, {"budget_bdt": 15000, "soil_type": "loam"}, "small budget, loamy soil"
    )

    assert "budget_bdt" in result["rejected"]
    assert "budget_bdt" not in result["accepted"]
    assert state.profile.get("budget_bdt") is None
    assert "budget_bdt" in result["still_missing"]

    # the soil claim IS supported by the message, so it's accepted normally
    assert result["accepted"]["soil_type"] == "loam"
    assert state.profile["soil_type"] == "loam"


def test_apply_profile_update_accepts_fully_valid_input():
    orch = Orchestrator()
    state = SessionState(id="t-valid")
    result = orch._apply_profile_update(
        state,
        {"budget_bdt": 20000, "farm_size_acres": 2, "soil_type": "sandy"},
        "I have 2 acres of sandy soil and a budget of 20000 BDT",
    )

    assert "rejected" not in result
    assert result["accepted"] == {
        "budget_bdt": 20000.0,
        "farm_size_acres": 2.0,
        "soil_type": "sandy",
    }
    assert state.profile["budget_bdt"] == 20000.0
    assert state.profile["farm_size_acres"] == 2.0
    assert state.profile["soil_type"] == "sandy"


def test_apply_profile_update_instruction_tells_model_to_ask_for_a_number():
    orch = Orchestrator()
    state = SessionState(id="t-instruction")
    result = orch._apply_profile_update(state, {"budget_bdt": 99999}, "small budget")
    assert "SPECIFIC NUMBER" in result["instruction"]


# --------------------------------------------------------------------------
# Orchestrator._backfill_profile — the "model skipped update_farm_profile" path
# --------------------------------------------------------------------------
def test_backfill_profile_drops_fabricated_number_keeps_field_missing():
    orch = Orchestrator()
    state = SessionState(id="t-backfill")
    orch._backfill_profile(
        state,
        "recommend_crops",
        {"soil_type": "loam", "budget_bdt": 99999},
        "small budget",
    )
    assert state.profile.get("budget_bdt") is None
    # soil_type came through a param whose value isn't itself validated against
    # the message in the backfill path's mapping semantics — but a vague
    # message still can't support ANY soil claim, so it must be dropped too.
    assert state.profile.get("soil_type") is None


def test_backfill_profile_accepts_supported_values():
    orch = Orchestrator()
    state = SessionState(id="t-backfill-ok")
    orch._backfill_profile(
        state,
        "recommend_crops",
        {"soil_type": "clay", "budget_bdt": 30000},
        "clay soil, 30000 BDT budget",
    )
    assert state.profile["soil_type"] == "clay"
    assert state.profile["budget_bdt"] == 30000.0


def test_backfill_profile_never_overwrites_an_already_known_field():
    orch = Orchestrator()
    state = SessionState(id="t-backfill-noclobber")
    state.profile["budget_bdt"] = 50000.0
    orch._backfill_profile(
        state, "recommend_crops", {"budget_bdt": 12345}, "budget is 12345 BDT"
    )
    assert state.profile["budget_bdt"] == 50000.0  # unchanged


# --------------------------------------------------------------------------
# Orchestrator._capture_intake — the deterministic extraction path
# --------------------------------------------------------------------------
class _StubLLM:
    """Minimal stand-in for LLMClient.extract_json — returns a fixed dict
    regardless of the prompt, simulating whatever the extraction model claims
    to have found (including a hallucinated figure)."""

    def __init__(self, fixed_result: dict):
        self._fixed_result = fixed_result

    async def extract_json(self, system: str, user: str) -> dict:
        return dict(self._fixed_result)


@pytest.mark.asyncio
async def test_capture_intake_drops_hallucinated_budget():
    orch = Orchestrator()
    orch.llm = _StubLLM({"budget_bdt": 15000})  # simulates the model's guess
    state = SessionState(id="t-intake-bad")

    await orch._capture_intake(state, "I have a small budget")

    assert state.profile.get("budget_bdt") is None
    assert "budget_bdt" in state.missing_fields()


@pytest.mark.asyncio
async def test_capture_intake_accepts_a_real_number():
    orch = Orchestrator()
    orch.llm = _StubLLM({"budget_bdt": 15000})
    state = SessionState(id="t-intake-good")

    await orch._capture_intake(state, "My budget is 15000 BDT")

    assert state.profile.get("budget_bdt") == 15000.0


@pytest.mark.asyncio
async def test_capture_intake_drops_hallucinated_soil_type():
    orch = Orchestrator()
    orch.llm = _StubLLM({"soil_type": "loam"})  # model's guess for a vague answer
    state = SessionState(id="t-intake-soil-bad")

    await orch._capture_intake(state, "the soil is pretty good here")

    assert state.profile.get("soil_type") is None
    assert "soil_type" in state.missing_fields()


@pytest.mark.asyncio
async def test_capture_intake_accepts_a_stated_soil_type():
    orch = Orchestrator()
    orch.llm = _StubLLM({"soil_type": "sandy"})
    state = SessionState(id="t-intake-soil-good")

    await orch._capture_intake(state, "it's sandy soil")

    assert state.profile.get("soil_type") == "sandy"
