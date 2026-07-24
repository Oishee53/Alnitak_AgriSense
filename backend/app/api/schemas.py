"""Pydantic request/response models for the API layer."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ---------- Farm profile ----------
class FarmProfile(BaseModel):
    """The minimum fields Tier-0 intake must collect."""

    location: Optional[str] = Field(None, description="Village / district / coords")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    farm_size_acres: Optional[float] = None
    soil_type: Optional[str] = Field(None, description="e.g. sandy, loam, clay")
    water_availability: Optional[str] = Field(
        None, description="e.g. rainfed, canal, tubewell, limited"
    )
    budget_bdt: Optional[float] = None
    target_season: Optional[str] = Field(None, description="e.g. Kharif, Rabi")

    def missing_fields(self) -> list[str]:
        """Return the names of required intake fields still unknown."""
        required = [
            "location",
            "farm_size_acres",
            "soil_type",
            "water_availability",
            "budget_bdt",
            "target_season",
        ]
        return [f for f in required if getattr(self, f) in (None, "")]


# ---------- Chat ----------
class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(
        None, description="Omit to start a new session; reuse to keep memory."
    )
    message: str


class TraceStep(BaseModel):
    """One entry in the visible agent trace."""

    step: int
    kind: Literal["thought", "tool_call", "tool_result", "message"]
    tool: Optional[str] = None
    params: Optional[dict[str, Any]] = None
    result: Optional[Any] = None
    summary: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    farm: FarmProfile
    trace: list[TraceStep] = []
    # Structured artifacts the agent may emit this turn:
    crop_options: Optional[dict[str, Any]] = None  # {options: [...], kb_references, note}
    season_plan: Optional[dict[str, Any]] = None
    financials: Optional[dict[str, Any]] = None
    # Tier-1 artifacts:
    fertilizer_schedule: Optional[dict[str, Any]] = None
    pest_risk: Optional[dict[str, Any]] = None
    scenario: Optional[dict[str, Any]] = None
    weather_alerts: Optional[dict[str, Any]] = None  # weather_advisory result (Tier 1)
    # Prior conversation, returned when rehydrating a session (memory).
    history: Optional[list[dict[str, str]]] = None


# ---------- Payment (bdapps CaaS) ----------
class CheckoutRequest(BaseModel):
    session_id: str
    subscriber_id: str = Field(
        ..., description="Farmer mobile number (01712345678 or tel:8801712345678)"
    )
    # Optional: when omitted, the server sums the priced item lines so the client
    # cannot dictate a total that disagrees with the basket.
    amount_bdt: Optional[float] = Field(
        None, description="If omitted, computed from item lines (qty × unit_price_bdt)."
    )
    items: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Basket lines: {name, qty, unit_price_bdt}.",
    )


class CheckoutResponse(BaseModel):
    success: bool
    external_trx_id: str
    status_code: str
    status_detail: str
    amount_bdt: float
    receipt: dict[str, Any]
    # The CaaS request + response as trace steps, so the frontend can drop the
    # charge straight into the visible agent trace.
    trace: list[TraceStep] = []
