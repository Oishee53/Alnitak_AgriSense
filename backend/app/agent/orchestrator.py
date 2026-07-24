"""The agent orchestrator — the tool-calling loop that makes this an *agent*.

Loop shape (per farmer turn):
    1. Build system prompt with the persistent farm profile + missing fields.
    2. Ask the LLM with the conversation + tool schemas.
    3. If the LLM requests tool call(s): run them, record each call and raw
       result to the trace, feed results back, repeat.
    4. When the LLM returns prose with no tool call, that's the reply.

Hand-written (no framework) so the trace captures every parameter sent and
value returned — the judge-verifiable grounding required by Tier-0 #8.
"""
from __future__ import annotations

import json
from typing import Any

from app.agent import trace as trace_mod
from app.agent.llm import LLMClient
from app.agent.prompts import build_system_prompt
from app.agent.tools import TOOLS, dispatch, tool_schemas
from app.api.schemas import ChatResponse, TraceStep
from app.memory.store import SessionState

MAX_STEPS = 10  # safety bound on LLM iterations per turn

# Which artifact slot each tool's result feeds (returned to the UI + persisted).
_ARTIFACT_SLOTS = {
    "recommend_crops": "crop_options",
    "build_season_plan": "season_plan",
    "compute_financials": "financials",
}

_REQUIRED_FIELDS = {
    "location",
    "farm_size_acres",
    "soil_type",
    "water_availability",
    "budget_bdt",
    "target_season",
}

# Profile backfill: if the LLM passes farm facts directly into other tools
# (skipping update_farm_profile), harvest them into the persistent profile
# anyway. tool -> {tool_param: profile_field}
_PROFILE_BACKFILL: dict[str, dict[str, str]] = {
    "get_weather": {"location": "location"},
    "recommend_crops": {
        "soil_type": "soil_type",
        "season": "target_season",
        "water_availability": "water_availability",
        "budget_bdt": "budget_bdt",
        "farm_size_acres": "farm_size_acres",
    },
    "build_season_plan": {"soil_type": "soil_type"},
    "compute_financials": {"farm_size_acres": "farm_size_acres"},
}


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


# Deterministic intake extraction — runs each turn while the profile is
# incomplete, so farm facts are captured (and traced) even if the model does
# not call update_farm_profile that turn.
INTAKE_EXTRACT_PROMPT = """\
You extract farm-profile fields from a Bangladeshi farmer's message and return
JSON. Include a field ONLY if the farmer explicitly states it in THIS message;
omit everything else. Return {} if nothing is stated.

Fields:
- location (string): place/village/district name
- farm_size_acres (number): acres. Convert units: 1 bigha = 0.33 acre, 1 katha = 0.0165 acre, 1 decimal = 0.01 acre
- soil_type (string): one of sandy, loam, clay, silt (map the farmer's word)
- water_availability (string): one of rainfed, limited, canal, tubewell (map the farmer's word)
- budget_bdt (number): in BDT. "15k"=15000, "1 lakh"=100000; for a range use the LOWER bound
- target_season (string): e.g. Aman, Boro, Rabi, Aus, Kharif-2, Kharif-1

Return a JSON object with only the stated fields.
"""

_NUMERIC_FIELDS = {"farm_size_acres", "budget_bdt"}


def _to_number(value: Any) -> float | None:
    """Best-effort coerce a value to a float; None if not parseable."""
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    s = value.strip().lower().replace(",", "").replace("bdt", "").replace("tk", "").strip()
    mult = 1.0
    if "lakh" in s or "lac" in s:
        mult = 100000.0
        s = s.replace("lakh", "").replace("lac", "").strip()
    elif s.endswith("k"):
        mult = 1000.0
        s = s[:-1].strip()
    try:
        return float(s) * mult
    except ValueError:
        return None


class Orchestrator:
    def __init__(self) -> None:
        self.llm = LLMClient()

    def _apply_profile_update(self, state: SessionState, fields: dict[str, Any]) -> dict[str, Any]:
        """Handle the intercepted update_farm_profile tool: merge known fields
        into persistent state and report what is still missing."""
        accepted = {}
        for key, value in fields.items():
            if key in _REQUIRED_FIELDS and value not in (None, ""):
                state.profile[key] = value
                accepted[key] = value
        missing = state.missing_fields()
        return {
            "ok": True,
            "accepted": accepted,
            "profile": state.profile,
            "still_missing": missing,
            "instruction": (
                "Ask targeted follow-ups for ONLY the still_missing fields."
                if missing
                else "Profile complete — proceed with get_weather → recommend_crops now."
            ),
        }

    async def _capture_intake(self, state: SessionState, message: str) -> None:
        """Deterministically extract farm facts from the message into the
        profile and record an inspectable intake step in the trace. Runs only
        while the profile is incomplete, so intake turns always produce a proper
        trace and facts are captured regardless of the model's tool choices."""
        if not state.missing_fields():
            return  # profile already complete — nothing to gather

        raw = await self.llm.extract_json(INTAKE_EXTRACT_PROMPT, message)
        captured: dict[str, Any] = {}
        for field in _REQUIRED_FIELDS:
            value = raw.get(field)
            if value in (None, ""):
                continue
            if field in _NUMERIC_FIELDS:
                num = _to_number(value)
                if num is None:
                    continue
                value = num
            state.profile[field] = value
            captured[field] = value

        missing = state.missing_fields()
        sid = state.id
        trace_mod.record(sid, "tool_call", tool="detect_farm_info", params={"message": message})
        trace_mod.record(
            sid,
            "tool_result",
            tool="detect_farm_info",
            result={
                "captured": captured,
                "profile": dict(state.profile),
                "still_missing": missing,
            },
            summary=(
                (f"captured {', '.join(captured)}; " if captured else "no new fields; ")
                + ("still missing: " + ", ".join(missing) if missing else "profile complete")
            ),
        )

    def _backfill_profile(self, state: SessionState, tool: str, params: dict[str, Any]) -> None:
        """If the LLM passed farm facts directly into a tool (skipping
        update_farm_profile), capture them into the persistent profile so the
        profile card stays in sync no matter how the model routes the info."""
        mapping = _PROFILE_BACKFILL.get(tool)
        if not mapping:
            return
        for param, field in mapping.items():
            value = params.get(param)
            if field in _REQUIRED_FIELDS and value not in (None, "") and not state.profile.get(field):
                state.profile[field] = value

    async def run(self, state: SessionState, message: str) -> ChatResponse:
        """Handle one farmer message end to end."""
        sid = state.id
        turn_start = len(trace_mod.get_trace(sid))

        # Deterministic intake: capture + trace any farm facts before reasoning,
        # so intake turns are always inspectable and facts are never lost.
        await self._capture_intake(state, message)

        conversation: list[dict[str, Any]] = [*state.history, {"role": "user", "content": message}]
        reply_text = ""
        # Dedupe cache: identical tool call (name + params) within one turn
        # reuses the first result instead of re-executing.
        called_cache: dict[str, Any] = {}

        for _ in range(MAX_STEPS):
            system = build_system_prompt(state.profile, state.missing_fields())
            resp = await self.llm.complete(
                system=system, messages=conversation, tools=tool_schemas()
            )

            tool_calls = resp.get("tool_calls") or []

            if resp.get("text") and not tool_calls:
                reply_text = resp["text"]
                trace_mod.record(sid, "message", summary=reply_text[:400])
                break

            if resp.get("text"):
                # Interleaved thinking the model emitted alongside tool calls.
                trace_mod.record(sid, "thought", summary=resp["text"][:400])

            conversation.append(resp["assistant_message"])

            for call in tool_calls:
                trace_mod.record(sid, "tool_call", tool=call["name"], params=call["input"])
                self._backfill_profile(state, call["name"], call["input"])
                cache_key = call["name"] + "::" + _dump(
                    dict(sorted(call["input"].items()))
                )
                try:
                    if cache_key in called_cache:
                        result: Any = called_cache[cache_key]
                        trace_mod.record(
                            sid,
                            "thought",
                            summary=f"duplicate {call['name']} call — reused earlier result",
                        )
                    elif call["name"] == "update_farm_profile":
                        result = self._apply_profile_update(state, call["input"])
                        called_cache[cache_key] = result
                    else:
                        result = await dispatch(call["name"], call["input"])
                        called_cache[cache_key] = result
                except Exception as e:  # feed errors back — the agent recovers
                    result = {"error": f"{type(e).__name__}: {e}"}
                trace_mod.record(
                    sid,
                    "tool_result",
                    tool=call["name"],
                    result=result,
                    summary=self._summarize_result(call["name"], result),
                )

                slot = _ARTIFACT_SLOTS.get(call["name"])
                if slot and isinstance(result, dict) and "error" not in result:
                    state.artifacts[slot] = result

                conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": _dump(result),
                    }
                )
        else:
            reply_text = (
                "I ran out of steps this turn — here is what I have so far. "
                "Ask me to continue for the rest."
            )
            trace_mod.record(sid, "message", summary="MAX_STEPS reached")

        turn_trace = [TraceStep(**s) for s in trace_mod.get_trace(sid)[turn_start:]]
        arts = state.artifacts
        return ChatResponse(
            session_id=sid,
            reply=reply_text,
            farm=state.farm_profile(),
            trace=turn_trace,
            crop_options=arts.get("crop_options"),
            season_plan=arts.get("season_plan"),
            financials=arts.get("financials"),
        )

    @staticmethod
    def _summarize_result(tool: str, result: Any) -> str:
        """One-line human summary for the trace panel."""
        if isinstance(result, dict):
            if "error" in result:
                return f"ERROR: {result['error']}"
            if tool == "get_weather":
                s = result.get("summary", {})
                return (
                    f"{result.get('location')}: {s.get('total_rain_mm')} mm rain / "
                    f"{s.get('rain_days')} rain-days, avg max {s.get('avg_t_max')}°C (open-meteo)"
                )
            if tool == "recommend_crops":
                names = [o["crop"] for o in result.get("options", [])[:3]]
                return "top: " + ", ".join(names)
            if tool == "build_season_plan":
                return (
                    f"{result.get('crop')}: sow {result.get('anchor_date')} → "
                    f"harvest {result.get('expected_harvest')} ({len(result.get('stages', []))} stages)"
                )
            if tool == "compute_financials":
                return (
                    f"cost {result.get('total_cost_bdt'):,} → revenue {result.get('revenue_bdt'):,} "
                    f"→ net {result.get('net_profit_bdt'):,} BDT (ROI {result.get('roi')})"
                )
            if tool == "update_farm_profile":
                miss = result.get("still_missing", [])
                return "profile updated; missing: " + (", ".join(miss) if miss else "none")
        if isinstance(result, list):
            return f"{len(result)} result(s)"
        return str(result)[:120]
