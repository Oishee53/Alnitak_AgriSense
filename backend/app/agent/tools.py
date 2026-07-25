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
from app.tools import (
    advisory,
    crops,
    fertilizer,
    finance,
    market,
    pests,
    scenario,
    season_plan,
    suppliers,
    weather,
)


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Optional[Callable[..., Awaitable[Any]]]
    # Params the ORCHESTRATOR may supply but the LLM must never pass — live
    # weather, chiefly. Deliberately absent from input_schema: a model that
    # can't see the field can't invent a forecast for it, and the orchestrator
    # fills in the real get_weather values instead.
    internal_params: tuple[str, ...] = ()

    def to_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    def accepts(self) -> set[str]:
        return set(self.input_schema.get("properties", {}).keys()) | set(self.internal_params)


TOOLS: dict[str, Tool] = {
    "update_farm_profile": Tool(
        name="update_farm_profile",
        description=(
            "Record farm profile fields the farmer just told you (location, farm "
            "size, soil type, water availability, budget, target season). Call "
            "this FIRST whenever the farmer reveals any of these. The result "
            "tells you which required fields are still missing so you can ask "
            "targeted follow-ups for ONLY those. "
            "NEVER INVENT farm_size_acres or budget_bdt: pass them ONLY when the "
            "farmer gave an actual figure. A vague description ('small budget', "
            "'not much land', 'enough money') has no number in it — OMIT the "
            "field and ask them for a specific number instead of estimating one. "
            "The server rejects any value it can't trace to a real number or "
            "figure in their message, so guessing wastes a turn. Likewise, only "
            "pass soil_type when their words clearly name sandy, loam, clay, or "
            "silt — a vague answer ('normal soil', 'not sure') should be omitted "
            "so you ask them to pick one of the four, not guessed."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "village/upazila/district"},
                "farm_size_acres": {
                    "type": "number",
                    "description": (
                        "farm size in acres (convert bigha: 1 bigha ≈ 0.33 acre). "
                        "ONLY if the farmer gave an actual number — never a guess "
                        "for a vague size like 'small' or 'a bit of land'."
                    ),
                },
                "soil_type": {
                    "type": "string",
                    "description": (
                        "sandy | loam | clay | silt — ONLY if their words clearly "
                        "name one of these four; never guess from a vague answer."
                    ),
                },
                "water_availability": {"type": "string", "description": "rainfed | limited | canal | tubewell/reliable"},
                "budget_bdt": {
                    "type": "number",
                    "description": (
                        "working budget in BDT. ONLY if the farmer gave an actual "
                        "figure ('15k', '1 lakh', a number) — never a guess for a "
                        "vague amount like 'small budget' or 'not much money'."
                    ),
                },
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
        internal_params=("weather_summary",),
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
    "build_fertilizer_schedule": Tool(
        name="build_fertilizer_schedule",
        description=(
            "Stage-by-stage fertilizer AND irrigation schedule for the chosen "
            "crop: exact kg of urea/TSP/MoP/gypsum/zinc per application, the date "
            "of each, the cost of each line, and organic alternatives. Doses come "
            "from the KB (BARC FRG-2018). Call get_weather FIRST — the live "
            "forecast is attached automatically so the tool can flag urea "
            "top-dressings that fall within 48h of heavy rain. Set "
            "use_organic=true if the farmer wants an organic/cowdung-based "
            "option. Use these numbers verbatim."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "crop": {"type": "string"},
                "soil_type": {"type": "string"},
                "farm_size_acres": {"type": "number"},
                "sowing_date": {"type": "string", "description": "ISO date; omit to use the recommended window"},
                "use_organic": {
                    "type": "boolean",
                    "description": "true if the farmer asked for organic/cowdung alternatives",
                },
            },
            "required": ["crop", "soil_type", "farm_size_acres"],
        },
        handler=fertilizer.build_fertilizer_schedule,
        internal_params=("weather_summary", "daily_weather"),
    ),
    "assess_pest_risk": Tool(
        name="assess_pest_risk",
        description=(
            "Predict the pests and diseases most likely to hit this crop RIGHT "
            "NOW, based on its growth stage and the live forecast. Returns each "
            "risk with symptom, scouting threshold, prevention steps, treatment, "
            "and estimated cost per acre — grounded in the KB IPM/plant-protection "
            "guides. Pass growth_stage (or days_after_sowing / sowing_date). "
            "Call get_weather FIRST — the live forecast is attached "
            "automatically, so risk levels reflect real conditions instead of a "
            "generic seasonal guess."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "crop": {"type": "string"},
                "growth_stage": {
                    "type": "string",
                    "description": "e.g. seedling, tillering, vegetative, flowering, fruiting, harvest",
                },
                "days_after_sowing": {"type": "integer", "description": "DAS, if known precisely"},
                "sowing_date": {"type": "string", "description": "ISO sowing date — DAS is computed from it"},
                "farm_size_acres": {"type": "number"},
            },
            "required": ["crop"],
        },
        handler=pests.assess_pest_risk,
        internal_params=("weather_summary", "daily_weather"),
    ),
    "simulate_scenario": Tool(
        name="simulate_scenario",
        description=(
            "Answer a what-if question with REAL recomputed numbers: 'what if "
            "rainfall drops 30%?', 'what if my budget is cut 40%?', 'what if the "
            "price falls 15%?'. Re-runs the finance engine with the perturbed "
            "input and returns baseline vs scenario side by side with every delta, "
            "plus alternative crops if the change makes this crop unviable. "
            "Percentages are SIGNED: a 30% drop is rainfall_pct=-30. Always use "
            "this for hypotheticals — never estimate the effect yourself."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "crop": {"type": "string"},
                "farm_size_acres": {"type": "number"},
                "rainfall_pct": {"type": "number", "description": "signed % change in rainfall, e.g. -30"},
                "budget_pct": {"type": "number", "description": "signed % change in budget, e.g. -40"},
                "new_budget_bdt": {"type": "number", "description": "absolute new budget, if the farmer states one"},
                "price_pct": {"type": "number", "description": "signed % change in selling price"},
                "yield_pct": {"type": "number", "description": "signed % change in yield"},
                "cost_pct": {"type": "number", "description": "signed % change in input costs"},
                "water_availability": {"type": "string", "description": "from the profile — buffers rainfall shocks"},
                "soil_type": {"type": "string"},
                "season": {"type": "string"},
            },
            "required": ["crop", "farm_size_acres"],
        },
        handler=scenario.simulate,
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
    "get_market_prices": Tool(
        name="get_market_prices",
        description=(
            "Market price intelligence (Tier 2): the current market price for a "
            "crop, its recent price history and trend, and a concrete "
            "SELL-NOW / STORE / WAIT recommendation with reasoning — accounting "
            "for whether the crop stores well. Call this when the farmer asks "
            "'what's the price', 'should I sell now or wait', 'where are prices "
            "heading', or when advising on harvest timing / marketing. Pass "
            "farm_size_acres to also get a gross-revenue estimate at today's "
            "price. Prices are seeded/mock — say so. Use these numbers verbatim."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "crop": {"type": "string"},
                "farm_size_acres": {"type": "number"},
                "expected_yield_per_acre": {
                    "type": "number",
                    "description": "ONLY if the farmer stated their own yield; else omit to use reference yield",
                },
            },
            "required": ["crop"],
        },
        handler=market.get_market_prices,
    ),
    "compare_suppliers": Tool(
        name="compare_suppliers",
        description=(
            "Marketplace / supplier comparison (Tier 2): sizes the fertilizer "
            "the farm actually needs (urea/TSP/MoP kg from the crop's FRG dose "
            "table × farm size), then prices that exact basket at every supplier "
            "and ranks them cheapest-first, with delivery/rating tradeoffs and "
            "the money saved vs the priciest. Call this when the farmer asks "
            "'where should I buy', 'which supplier is cheapest', or about input "
            "shopping. Pass soil_type so sandy-soil MoP is sized right. The "
            "supplier catalog is seeded/mock — say so. Use these numbers verbatim."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "crop": {"type": "string"},
                "farm_size_acres": {"type": "number"},
                "soil_type": {"type": "string"},
            },
            "required": ["crop", "farm_size_acres"],
        },
        handler=suppliers.compare_suppliers,
    ),
    "search_knowledge_base": Tool(
        name="search_knowledge_base",
        description=(
            "FALLBACK knowledge lookup: retrieve grounded agronomic facts from the "
            "local knowledge base (public BRRI/BARC/DAE extension materials) for "
            "questions no specialised tool covers — varieties, spacing, seed rate, "
            "storage, general practice. "
            "Do NOT use this for fertilizer doses/timing (use "
            "build_fertilizer_schedule), pest or disease risk (use "
            "assess_pest_risk), what-if questions (use simulate_scenario), crop "
            "choice (use recommend_crops), the calendar (use build_season_plan), "
            "or money (use compute_financials) — those tools return exact, costed, "
            "dated numbers, while this returns only prose to read."
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
    allowed = tool.accepts()
    clean = {k: v for k, v in params.items() if k in allowed}
    return await tool.handler(**clean)
