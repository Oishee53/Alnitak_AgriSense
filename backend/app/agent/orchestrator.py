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
import re
from typing import Any

from app.agent import trace as trace_mod
from app.agent.llm import LLMClient
from app.agent.prompts import build_system_prompt
from app.agent.tools import TOOLS, dispatch, tool_schemas
from app.api.schemas import ChatResponse, TraceStep
from app.memory.store import SessionState

MAX_STEPS = 10  # safety bound on LLM iterations per turn

# One numeral system per reply, enforced in code — the model mixes ০-৯ and 0-9
# when writing Bangla no matter what the prompt says. Every reply is first
# folded to Western digits (kills any mixing), then, for Bangla-mode replies,
# mapped wholesale to Bengali numerals. Pure character translation both ways:
# deterministic, nothing the model can garble.
_BN_TO_WESTERN = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
_WESTERN_TO_BN = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")


def _normalize_digits(text: str, lang: str | None) -> str:
    western = text.translate(_BN_TO_WESTERN)
    if (lang or "en").lower() == "bn":
        return western.translate(_WESTERN_TO_BN)
    return western

# Which artifact slot each tool's result feeds (returned to the UI + persisted).
_ARTIFACT_SLOTS = {
    "recommend_crops": "crop_options",
    "build_season_plan": "season_plan",
    "compute_financials": "financials",
    "build_fertilizer_schedule": "fertilizer_schedule",
    "assess_pest_risk": "pest_risk",
    "simulate_scenario": "scenario",
    "weather_advisory": "weather_alerts",
    "get_market_prices": "market",
    "compare_suppliers": "suppliers",
}

# Artifacts that describe ONE chosen crop. When the farmer switches crop, any of
# these left over from the previous crop are stale and must be dropped — else the
# UI shows, say, a Brinjal season plan next to Aman market prices. Each carries a
# "crop" field we compare against.
_CROP_KEYED_SLOTS = {
    "season_plan",
    "financials",
    "fertilizer_schedule",
    "pest_risk",
    "scenario",
    "weather_alerts",
    "market",
    "suppliers",
}


def _evict_stale_crop_artifacts(artifacts: dict[str, Any], slot: str, result: Any) -> None:
    """Drop crop-keyed artifacts belonging to a different crop than `result`.

    Called after storing a crop-keyed artifact: if the farmer has moved to a new
    crop, the previous crop's plan/finance/market/supplier/etc. panels are
    removed so every visible panel is about the same, current crop.
    """
    if slot not in _CROP_KEYED_SLOTS or not isinstance(result, dict):
        return
    new_crop = result.get("crop")
    if not new_crop:
        return
    for other in _CROP_KEYED_SLOTS - {slot}:
        art = artifacts.get(other)
        if isinstance(art, dict) and art.get("crop") and art["crop"] != new_crop:
            artifacts.pop(other, None)

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
    "build_fertilizer_schedule": {
        "soil_type": "soil_type",
        "farm_size_acres": "farm_size_acres",
    },
    "assess_pest_risk": {"farm_size_acres": "farm_size_acres"},
    "simulate_scenario": {
        "farm_size_acres": "farm_size_acres",
        "water_availability": "water_availability",
        "soil_type": "soil_type",
        "season": "target_season",
    },
}


# Tools whose advice should be grounded in the live forecast. If the model
# calls one after get_weather but forgets to pass the weather through, the
# orchestrator injects the real result rather than letting the tool fall back to
# a stage-only (ungrounded) answer.
_WEATHER_CONSUMERS = {
    "assess_pest_risk": ("weather_summary", "daily_weather"),
    "build_fertilizer_schedule": ("weather_summary", "daily_weather"),
    "recommend_crops": ("weather_summary", None),
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

NEVER INVENT A NUMBER. farm_size_acres and budget_bdt exist ONLY when the
farmer gave an actual figure (a digit, "1 lakh", "15k", a spelled-out number,
or a clear unit conversion like "2 bigha"). A vague/qualitative description —
"small budget", "not much land", "enough money", "a decent amount" — has NO
number in it. Omit the field entirely in that case; do NOT estimate, round, or
pick a "reasonable" figure to fill it. Example: "I have a small budget" ->
budget_bdt is NOT included (there is nothing to convert). "My budget is 15k"
-> budget_bdt: 15000.

NEVER GUESS A SOIL TYPE. Only set soil_type when the farmer's own words
clearly name a texture (sandy/বেলে, loam/দোআঁশ, clay/এঁটেল, silt/পলি) or an
unambiguous synonym. A vague answer — "normal soil", "good soil", "not sure",
"black soil" — does not clearly mean one of the four; omit soil_type rather
than picking the closest-sounding one.

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


# Deterministic backstop against a well-documented failure mode: asked for a
# number, a model will sometimes invent a plausible one rather than admit the
# farmer never gave one — e.g. "small budget" silently becoming budget_bdt=15000.
# _to_number() alone can't catch this: once the model has already turned "small"
# into "15000", the string parses fine. So this checks the ORIGINAL farmer
# message instead: if it contains no digit, no Bengali numeral, no scale word
# (lakh/k/thousand/হাজার), and no spelled-out number, there is no number in it
# for the model to have found — any numeric value attributed to it must have
# been fabricated and is dropped, regardless of what the model returned.
# Known limitation: this is a message-level gate, not per-field — a message
# with a number for ONE field ("5 acres, small budget") won't stop a model
# from also inventing a figure for the OTHER field it correctly left vague.
_NUMBER_WORD_RE = re.compile(
    r"\b("
    r"lakh|lac|crore|hazar|thousand|"
    r"one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
    r"twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|"
    r"এক|দুই|তিন|চার|পাঁচ|ছয়|সাত|আট|নয়|দশ|বিশ|ত্রিশ|চল্লিশ|পঞ্চাশ|লাখ|হাজার|কোটি"
    r")\b",
    re.IGNORECASE,
)


def _message_has_number(message: str) -> bool:
    """True if the farmer's message contains an actual number signal: a
    Western or Bengali digit, a scale word (lakh/k/thousand/হাজার/লাখ), or a
    spelled-out number. False means nothing in the message could honestly
    become a figure — see the module note above."""
    translated = (message or "").translate(_BN_TO_WESTERN)
    if any(ch.isdigit() for ch in translated):
        return True
    return bool(_NUMBER_WORD_RE.search(message or ""))


# Soil-type intake validation is intentionally STRICTER than
# app.tools.seed_data.normalize_soil(), which defaults anything unrecognized to
# "loam" — a reasonable computational fallback deep in the crop/fertilizer math,
# but wrong for INTAKE: silently guessing a texture the farmer never confirmed
# is exactly the hallucination this fix targets. Order mirrors normalize_soil's
# precedence (sand > clay > silt > loam) so a phrase like "sandy loam" resolves
# to the same texture in both places.
_SOIL_SYNONYMS: dict[str, tuple[str, ...]] = {
    "sandy": ("sand", "বেলে"),
    "clay": ("clay", "এঁটেল", "কাদা"),
    "silt": ("silt", "পলি"),
    "loam": ("loam", "দোআঁশ"),
}


def _canonical_soil_type(raw: str) -> str | None:
    """Map free text to sandy/loam/clay/silt ONLY if it clearly says so.
    Anything else (vague, unrecognized, or empty) returns None so the field
    stays 'missing' and the agent asks the farmer to pick one of the four
    types — instead of the profile silently recording garbage."""
    s = (raw or "").strip().lower()
    if not s:
        return None
    for canon, keywords in _SOIL_SYNONYMS.items():
        if any(kw in s for kw in keywords):
            return canon
    return None


def _validate_field(field: str, value: Any, message: str) -> tuple[Any, str | None]:
    """Validate a candidate profile-field value before trusting it.

    Returns (clean_value, None) if it's acceptable, or (None, reason) if it
    must be rejected — the caller then leaves the field out of the profile, so
    it stays in missing_fields() and the agent asks again, instead of a
    hallucinated number or a made-up soil texture entering memory.
    """
    if field in _NUMERIC_FIELDS:
        if not _message_has_number(message):
            return None, (
                "the farmer's message has no digit or number word — a figure "
                "here would have to be invented, so it was dropped"
            )
        num = _to_number(value)
        if num is None:
            return None, f"'{value}' could not be parsed as a number"
        return num, None
    if field == "soil_type":
        # Derived from the ORIGINAL MESSAGE, not the model's returned `value`.
        # A model can echo back a plausible-looking canonical string (e.g. map
        # "good soil" -> "loam") that would pass a check on `value` alone —
        # that IS the hallucination this guards against. Re-deriving from the
        # farmer's own words means the model's classification can't quietly
        # substitute a texture nothing in the message actually supports.
        canon = _canonical_soil_type(message)
        if canon is None:
            return None, (
                f"the farmer's message doesn't clearly name sandy, loam, clay, "
                f"or silt — '{value}' was not trusted"
            )
        return canon, None
    return value, None


class Orchestrator:
    def __init__(self) -> None:
        self.llm = LLMClient()

    def _apply_profile_update(
        self, state: SessionState, fields: dict[str, Any], message: str
    ) -> dict[str, Any]:
        """Handle the intercepted update_farm_profile tool: merge known fields
        into persistent state and report what is still missing.

        Runs budget/farm-size/soil-type through _validate_field first: a
        number the farmer's message can't support, or a soil description that
        doesn't clearly name one of the four textures, is REJECTED rather than
        recorded — the field stays missing and the model is told to ask again
        for a specific value instead of quietly trusting its own guess.
        """
        accepted: dict[str, Any] = {}
        rejected: dict[str, str] = {}
        for key, value in fields.items():
            if key not in _REQUIRED_FIELDS or value in (None, ""):
                continue
            clean, reason = _validate_field(key, value, message)
            if reason is not None:
                rejected[key] = reason
                continue
            state.profile[key] = clean
            accepted[key] = clean

        missing = state.missing_fields()
        instruction = (
            "Ask targeted follow-ups for ONLY the still_missing fields."
            if missing
            else "Profile complete — proceed with get_weather → recommend_crops now."
        )
        if rejected:
            instruction = (
                "Some values were REJECTED — see 'rejected' below, do NOT treat "
                "them as known. For a rejected budget_bdt or farm_size_acres, ask "
                "the farmer for a SPECIFIC NUMBER (e.g. 'Could you give me a "
                "number, like 20000 BDT or 1 lakh?' / 'How many acres or bigha "
                "exactly?'). For a rejected soil_type, ask them to pick sandy, "
                "loam, clay, or silt (briefly describe each if unsure) instead "
                "of guessing. " + instruction
            )
        result: dict[str, Any] = {
            "ok": True,
            "accepted": accepted,
            "profile": state.profile,
            "still_missing": missing,
            "instruction": instruction,
        }
        if rejected:
            result["rejected"] = rejected
        return result

    async def _capture_intake(self, state: SessionState, message: str) -> None:
        """Deterministically extract farm facts from the message into the
        profile and record an inspectable intake step in the trace. Runs only
        while the profile is incomplete, so intake turns always produce a proper
        trace and facts are captured regardless of the model's tool choices.

        Same validation as _apply_profile_update: a number the message can't
        support, or a soil description that isn't clearly one of the four
        textures, is rejected rather than recorded (see _validate_field)."""
        if not state.missing_fields():
            return  # profile already complete — nothing to gather

        raw = await self.llm.extract_json(INTAKE_EXTRACT_PROMPT, message)
        captured: dict[str, Any] = {}
        rejected: dict[str, str] = {}
        for field in _REQUIRED_FIELDS:
            value = raw.get(field)
            if value in (None, ""):
                continue
            clean, reason = _validate_field(field, value, message)
            if reason is not None:
                rejected[field] = reason
                continue
            state.profile[field] = clean
            captured[field] = clean

        missing = state.missing_fields()
        sid = state.id
        trace_mod.record(sid, "tool_call", tool="detect_farm_info", params={"message": message})

        summary_parts = []
        if captured:
            summary_parts.append(f"captured {', '.join(captured)}")
        if rejected:
            summary_parts.append(f"rejected {', '.join(rejected)} (needs a real value from the farmer)")
        if not captured and not rejected:
            summary_parts.append("no new fields")
        summary_parts.append("still missing: " + ", ".join(missing) if missing else "profile complete")

        trace_mod.record(
            sid,
            "tool_result",
            tool="detect_farm_info",
            result={
                "captured": captured,
                "rejected": rejected,
                "profile": dict(state.profile),
                "still_missing": missing,
            },
            summary="; ".join(summary_parts),
        )

    @staticmethod
    def _inject_weather(
        tool: str, params: dict[str, Any], last_weather: dict[str, Any] | None
    ) -> list[str]:
        """Attach the real get_weather result to weather-consuming tools.

        These params are not advertised in the tool schemas, so a well-behaved
        model never sends them — but models have been observed inventing a
        plausible-looking forecast anyway. Anything the model supplies here is
        therefore DISCARDED and replaced with the real call's values (or dropped
        entirely if we have no real forecast yet). Returns the param names set,
        so the trace shows where the grounding came from.
        """
        spec = _WEATHER_CONSUMERS.get(tool)
        if not spec:
            return []

        injected: list[str] = []
        for key, source in zip(spec, ("summary", "daily")):
            if key is None:
                continue
            params.pop(key, None)  # never trust a model-supplied forecast
            value = (last_weather or {}).get(source)
            if value:
                params[key] = value
                injected.append(key)
        return injected

    def _backfill_profile(
        self, state: SessionState, tool: str, params: dict[str, Any], message: str
    ) -> None:
        """If the LLM passed farm facts directly into a tool (skipping
        update_farm_profile), capture them into the persistent profile so the
        profile card stays in sync no matter how the model routes the info.
        Same validation as _apply_profile_update — a fabricated number or an
        unrecognized soil description is silently dropped, not backfilled."""
        mapping = _PROFILE_BACKFILL.get(tool)
        if not mapping:
            return
        for param, field in mapping.items():
            value = params.get(param)
            if field not in _REQUIRED_FIELDS or value in (None, "") or state.profile.get(field):
                continue
            clean, reason = _validate_field(field, value, message)
            if reason is None:
                state.profile[field] = clean

    async def run(
        self, state: SessionState, message: str, lang: str | None = None
    ) -> ChatResponse:
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
        # Last real get_weather result, reused to ground later tool calls.
        last_weather: dict[str, Any] | None = state.artifacts.get("weather")

        for _ in range(MAX_STEPS):
            system = build_system_prompt(state.profile, state.missing_fields(), lang)
            resp = await self.llm.complete(
                system=system, messages=conversation, tools=tool_schemas()
            )

            tool_calls = resp.get("tool_calls") or []

            if resp.get("text") and not tool_calls:
                reply_text = _normalize_digits(resp["text"], lang)
                trace_mod.record(sid, "message", summary=reply_text[:400])
                break

            if resp.get("text"):
                # Interleaved thinking the model emitted alongside tool calls.
                trace_mod.record(sid, "thought", summary=resp["text"][:400])

            conversation.append(resp["assistant_message"])

            for call in tool_calls:
                injected = self._inject_weather(call["name"], call["input"], last_weather)
                trace_mod.record(sid, "tool_call", tool=call["name"], params=call["input"])
                if injected:
                    trace_mod.record(
                        sid,
                        "thought",
                        summary=(
                            f"grounding {call['name']} in the live forecast: filled in "
                            f"{', '.join(injected)} from this session's get_weather result"
                        ),
                    )
                self._backfill_profile(state, call["name"], call["input"], message)
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
                        result = self._apply_profile_update(state, call["input"], message)
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
                    # Switching crop invalidates the other crop's panels.
                    _evict_stale_crop_artifacts(state.artifacts, slot, result)

                # Remember the live forecast so later tools this turn — and in
                # later turns — can be grounded in it.
                if (
                    call["name"] == "get_weather"
                    and isinstance(result, dict)
                    and "error" not in result
                ):
                    last_weather = result
                    state.artifacts["weather"] = result

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
            fertilizer_schedule=arts.get("fertilizer_schedule"),
            pest_risk=arts.get("pest_risk"),
            scenario=arts.get("scenario"),
            weather_alerts=arts.get("weather_alerts"),
            market=arts.get("market"),
            suppliers=arts.get("suppliers"),
            disease=arts.get("disease"),
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
            if tool == "weather_advisory":
                alerts = result.get("alerts", [])
                fw = result.get("forecast_window", {})
                return (
                    f"{len(alerts)} weather alert(s) over {fw.get('days')}-day forecast "
                    f"({fw.get('total_rain_mm')} mm rain) for {result.get('crop')}"
                )
            if tool == "update_farm_profile":
                miss = result.get("still_missing", [])
                return "profile updated; missing: " + (", ".join(miss) if miss else "none")
            if tool == "build_fertilizer_schedule":
                alerts = sum(
                    1 for s in result.get("fertilizer_schedule", []) if "weather_alert" in s
                )
                cost = result.get("total_fertilizer_cost_bdt")
                # cost is None for crops with no published dose table
                cost_txt = f"{cost:,} BDT total" if cost is not None else "timing only (no published doses)"
                return (
                    f"{result.get('crop')}: {len(result.get('fertilizer_schedule', []))} applications + "
                    f"{len(result.get('irrigation_schedule', []))} irrigations, {cost_txt}"
                    + (f" — {alerts} rain-delay alert(s)" if alerts else "")
                )
            if tool == "assess_pest_risk":
                active = result.get("active_risks", [])
                high = [r["name"] for r in active if r.get("risk") == "high"]
                return (
                    f"{result.get('crop')} at {result.get('days_after_sowing')} DAS: "
                    f"{len(active)} active risk(s)"
                    + (f"; HIGH: {', '.join(high)}" if high else "")
                )
            if tool == "simulate_scenario":
                return (
                    f"{result.get('crop')} {result.get('scenario_applied')}: net profit "
                    f"{result.get('baseline', {}).get('net_profit_bdt', 0):,} → "
                    f"{result.get('scenario', {}).get('net_profit_bdt', 0):,} BDT "
                    f"({result.get('net_profit_change_bdt', 0):+,.0f})"
                )
            if tool == "get_market_prices":
                t = result.get("trend", {})
                return (
                    f"{result.get('crop')}: {result.get('current_price_bdt')} BDT/"
                    f"{result.get('unit')} ({t.get('direction')} "
                    f"{t.get('change_pct_recent', 0):+g}%) → {result.get('recommendation')}"
                )
            if tool == "compare_suppliers":
                sups = result.get("suppliers", [])
                best = sups[0] if sups else {}
                return (
                    f"{result.get('crop')}: {len(sups)} suppliers priced; cheapest "
                    f"{best.get('name')} {best.get('total_input_cost_bdt', 0):,} BDT "
                    f"(saves {result.get('savings_vs_worst_bdt', 0):,})"
                )
        if isinstance(result, list):
            return f"{len(result)} result(s)"
        return str(result)[:120]
