"""Agent-trace endpoints.

The trace is a first-class deliverable (Tier-0 #8): a judge must be able to
confirm every number came from a real tool call. We expose the recorded trace
for a session both as a snapshot and (optionally) as a live stream.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.agent import trace as trace_mod
from app.memory import store

router = APIRouter(prefix="/api/trace", tags=["trace"])


@router.get("/{session_id}")
def get_trace(session_id: str) -> dict:
    """Return the full recorded trace for a session.

    Served from the persisted store (survives backend restarts); the in-memory
    trace is used when it is ahead (e.g. a turn in progress not yet saved).
    """
    mem = trace_mod.get_trace(session_id)
    persisted = store.load_trace(session_id)
    trace = mem if len(mem) > len(persisted) else persisted
    return {"session_id": session_id, "trace": trace}


@router.get("/{session_id}/stream")
async def stream_trace(session_id: str) -> StreamingResponse:
    """Server-Sent Events stream of trace steps as they happen.

    TODO: wire to an asyncio queue fed by the orchestrator so the frontend
    trace panel updates live during a turn.
    """

    async def event_gen():
        async for step in trace_mod.subscribe(session_id):
            yield f"data: {step}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")
