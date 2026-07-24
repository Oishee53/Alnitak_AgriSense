"""Agent trace recorder (Tier-0 #8).

Records every thought, tool call (params sent), and tool result (raw values
returned) per session, so the frontend/judge can verify grounding. In-memory
for the hackathon; swap the backing store for the DB later if needed.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, AsyncIterator

from app.api.schemas import TraceStep

# session_id -> list of trace steps
_TRACES: dict[str, list[TraceStep]] = defaultdict(list)
# session_id -> subscriber queues for live streaming
_SUBSCRIBERS: dict[str, list[asyncio.Queue]] = defaultdict(list)


def record(
    session_id: str,
    kind: str,
    *,
    tool: str | None = None,
    params: dict[str, Any] | None = None,
    result: Any | None = None,
    summary: str | None = None,
) -> TraceStep:
    steps = _TRACES[session_id]
    step = TraceStep(
        step=len(steps) + 1,
        kind=kind,  # type: ignore[arg-type]
        tool=tool,
        params=params,
        result=result,
        summary=summary,
    )
    steps.append(step)
    for q in _SUBSCRIBERS[session_id]:
        q.put_nowait(step)
    return step


def get_trace(session_id: str) -> list[dict[str, Any]]:
    return [s.model_dump() for s in _TRACES.get(session_id, [])]


def reset(session_id: str) -> None:
    _TRACES.pop(session_id, None)


async def subscribe(session_id: str) -> AsyncIterator[str]:
    """Yield trace steps as JSON as they are recorded (for SSE)."""
    q: asyncio.Queue = asyncio.Queue()
    _SUBSCRIBERS[session_id].append(q)
    try:
        while True:
            step: TraceStep = await q.get()
            yield step.model_dump_json()
    finally:
        _SUBSCRIBERS[session_id].remove(q)
