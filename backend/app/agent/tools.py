"""Tool registry: the bridge between the LLM's tool calls and Python functions.

Each tool exposes:
  - a JSON schema (name, description, input_schema) sent to the LLM, and
  - an async `handler(**kwargs)` the orchestrator invokes when the LLM calls it.

`update_farm_profile` is special: its handler is None and the orchestrator
intercepts it to mutate session state (conversational intake, Tier-0 #1).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

from app.rag import retriever
from app.tools import advisory, crops, finance, season_plan, weather


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Optional[Callable[..., Awaitable[Any]]]

    def to_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


TOOLS: dict[str, Tool] = {
    "update_farm_profile": Tool(
        name="update_farm_profile",
        description=(
            "Record farm profile fields the farmer just told you (location, farm "
            "size, soil type, water availability, budget, target season). Call "
            "this FIRST whenever the farmer reveals any of these. The result "
            "tells you which required fields are still missing so you can ask "
            "targeted follow-ups for ONLY those."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "village/upazila/district"},
                "farm_size_acres": {"type": "number", "description": "farm size in acres (convert bigha: 1 bigha ≈ 0.33 acre)"},
                "soil_type": {"type": "string", "description": "sandy | loam | clay | silt (or farmer's words)"},
                "water_availability": {"type": "string", "description": "rainfed | limited | canal | tubewell/reliable"},
                "budget_bdt": {"type": "number", "description": "working budget in BDT"},
                "target_season": {"type": "string", "description": "e.g. Aman/Kharif-2, Boro, Rabi"},
            },
        },
        handler=None,  # intercepted by the orchestrator (mutates session state)
    ),
    "get_weather": Tool(
        name="get_weather",
        description=(
            "Fetch REAL current + forecast weather (rainfall, temperature) for a "
            "location via the Open-Meteo API. ALWAYS call this before crop or "
            "fertilizer-timing advice. Never invent weather."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "latitude": {"type": "number"},
                "longitude": {"type": "number"},
                "days": {"type": "integer", "default": 7, "minimum": 1, "maximum": 16},
            },
            "required": ["location"],
        },
        handler=weather.get_weather,
    ),
    "recommend_crops": Tool(
        name="recommend_crops",
        description=(
            "Rank candidate crops for the farm profile, season, and live weather. "
            "First hard-excludes infeasible crops (wrong season / water impossible "
            "/ over budget) with reasons, then ranks the rest by suitability + "
            "risk-adjusted profit. Returns feasible `options`, an `excluded` list "
            "with reasons, and KB citations. Pass the weather_summary from "
            "get_weather. Set `priority` from the farmer's stated preference."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "soil_type": {"type": "string"},
                "season": {"type": "string"},
                "water_availability": {"type": "string"},
                "weather_summary": {"type": "object", "description": "the `summary` object returned by get_weather"},
                "budget_bdt": {"type": "number"},
                "farm_size_acres": {"type": "number"},
                "priority": {
                    "type": "string",
                    "enum": ["balanced", "profit", "safe"],
                    "description": "ranking bias: 'profit' if the farmer wants max return, 'safe' if they want low risk, else 'balanced' (default)",
                },
            },
            "required": ["soil_type", "season"],
        },
        handler=crops.recommend_crops,
    ),
    "build_season_plan": Tool(
        name="build_season_plan",
        description=(
            "Produce a dated calendar for the chosen crop from land preparation "
            "to harvest (sowing window, fertilizer timing, irrigation, weed and "
            "pest checkpoints, harvest), grounded in the KB crop calendar."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "crop": {"type": "string"},
                "sowing_date": {"type": "string", "description": "ISO date; omit to use the recommended window"},
                "soil_type": {"type": "string"},
            },
            "required": ["crop"],
        },
        handler=season_plan.build_season_plan,
    ),
    "compute_financials": Tool(
        name="compute_financials",
        description=(
            "Itemized cost breakdown + expected yield, revenue, net profit, ROI "
            "and break-even for a crop and farm size. Deterministic math over "
            "reference data — use these numbers verbatim, never recompute."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "crop": {"type": "string"},
                "farm_size_acres": {"type": "number"},
                "inputs": {
                    "type": "object",
                    "description": (
                        "cost-line overrides {item: {qty, unit_cost}} — ONLY if the "
                        "farmer explicitly stated their own costs; otherwise OMIT"
                    ),
                },
                "expected_price_bdt_per_unit": {
                    "type": "number",
                    "description": "ONLY if the farmer explicitly stated a selling price; NEVER invent one — omit to use reference data",
                },
                "expected_yield_per_acre": {
                    "type": "number",
                    "description": "ONLY if the farmer explicitly stated their own yield; NEVER invent one — omit to use reference data",
                },
            },
            "required": ["crop", "farm_size_acres"],
        },
        handler=finance.compute_financials,
    ),
    "weather_advisory": Tool(
        name="weather_advisory",
        description=(
            "PROACTIVE weather-triggered advice (Tier 1). Watches the LIVE "
            "forecast against the chosen crop's upcoming plan actions and returns "
            "dated adjustments — e.g. delay a urea top-dress before heavy rain, "
            "skip an irrigation the rain will cover, spray in a dry gap, or harvest "
            "before a storm. Call this after a season plan is chosen, or whenever "
            "the farmer asks about weather risk or fertilizer/irrigation timing. "
            "Pass the crop and the farm location; it fetches the real forecast and "
            "builds the dated plan itself. Surface each alert with its date, the "
            "forecast numbers, and the because."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "crop": {"type": "string"},
                "location": {"type": "string", "description": "farm location for the forecast"},
                "sowing_date": {"type": "string", "description": "ISO date if the crop is already sown; omit to use the recommended window"},
                "soil_type": {"type": "string"},
                "water_availability": {"type": "string"},
                "days": {"type": "integer", "default": 16, "minimum": 1, "maximum": 16},
            },
            "required": ["crop", "location"],
        },
        handler=advisory.weather_advisory,
    ),
    "search_knowledge_base": Tool(
        name="search_knowledge_base",
        description=(
            "Retrieve grounded agronomic facts (crop calendars, fertilizer doses, "
            "soil suitability, pest management) from the local knowledge base "
            "built from public BRRI/BARC/DAE extension materials. Use this for "
            "any agronomy question instead of answering from memory."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "k": {"type": "integer", "default": 4, "minimum": 1, "maximum": 8},
            },
            "required": ["query"],
        },
        handler=retriever.search,
    ),
}


def tool_schemas() -> list[dict[str, Any]]:
    """List of tool schemas to advertise to the LLM."""
    return [t.to_schema() for t in TOOLS.values()]


async def dispatch(name: str, params: dict[str, Any]) -> Any:
    """Invoke a tool by name. Unknown params are dropped defensively."""
    if name not in TOOLS:
        raise KeyError(f"Unknown tool: {name}")
    tool = TOOLS[name]
    if tool.handler is None:
        raise RuntimeError(f"Tool {name} must be handled by the orchestrator")
    allowed = set(tool.input_schema.get("properties", {}).keys())
    clean = {k: v for k, v in params.items() if k in allowed}
    return await tool.handler(**clean)
