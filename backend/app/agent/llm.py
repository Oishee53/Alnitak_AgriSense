"""LLM provider abstraction.

Default: OpenAI (the team's credits). Everything the agent needs sits behind
this thin interface, so the provider can be swapped without touching the loop.
"""
from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI

from app.config import settings


class LLMClient:
    """Thin wrapper around the OpenAI chat-completions + tool-calling API."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.llm_model
        self._client: AsyncOpenAI | None = None  # built lazily on first use

    def _get_client(self) -> AsyncOpenAI:
        """Construct the OpenAI client on first use so the server can boot
        (health, weather, etc.) even before OPENAI_API_KEY is configured."""
        if self._client is None:
            if not settings.openai_api_key:
                raise RuntimeError(
                    "OPENAI_API_KEY is not set. Add it to backend/.env to use the agent."
                )
            kwargs: dict[str, Any] = {"api_key": settings.openai_api_key}
            if settings.openai_base_url:
                kwargs["base_url"] = settings.openai_base_url
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    @staticmethod
    def _to_openai_tools(tools: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
        """Convert our internal tool schema to OpenAI's function-tool format."""
        if not tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t["input_schema"],
                },
            }
            for t in tools
        ]

    async def complete(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Return a normalized response:

            {
              "text": str | None,             # assistant prose, if any
              "tool_calls": [{"id","name","input"}],  # zero or more
              "stop_reason": str,
            }
        """
        oa_messages = [{"role": "system", "content": system}, *messages]
        kwargs: dict[str, Any] = {}
        oa_tools = self._to_openai_tools(tools)
        if oa_tools:
            kwargs["tools"] = oa_tools
        resp = await self._get_client().chat.completions.create(
            model=self.model,
            messages=oa_messages,
            max_tokens=settings.llm_max_tokens,
            **kwargs,
        )
        choice = resp.choices[0]
        msg = choice.message

        tool_calls = []
        for tc in msg.tool_calls or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_calls.append({"id": tc.id, "name": tc.function.name, "input": args})

        # Raw assistant message in OpenAI format — must be appended to the
        # conversation before the matching role="tool" results.
        assistant_message: dict[str, Any] = {
            "role": "assistant",
            "content": msg.content or "",
        }
        if msg.tool_calls:
            assistant_message["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments or "{}",
                    },
                }
                for tc in msg.tool_calls
            ]

        return {
            "text": msg.content,
            "tool_calls": tool_calls,
            "assistant_message": assistant_message,
            "stop_reason": choice.finish_reason,
        }

    async def extract_json(self, system: str, user: str) -> dict[str, Any]:
        """Structured JSON extraction (used for deterministic intake capture).

        Uses OpenAI JSON mode so the result is always valid JSON. Returns {} on
        any failure so the caller can proceed without the extraction.
        """
        try:
            resp = await self._get_client().chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
                max_tokens=300,
            )
            return json.loads(resp.choices[0].message.content or "{}")
        except Exception:
            return {}
