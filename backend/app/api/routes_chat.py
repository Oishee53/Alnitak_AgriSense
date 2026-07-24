"""Chat endpoints — the single entry point a farmer talks to.

The heavy lifting lives in the agent orchestrator; this layer adapts
HTTP <-> agent and persists the turn to memory.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from app.api.schemas import ChatRequest, ChatResponse
from app.agent.orchestrator import Orchestrator
from app.memory import store

router = APIRouter(prefix="/api", tags=["chat"])

_orchestrator = Orchestrator()

# One lock per session id: concurrent requests on the SAME session serialize,
# so double-clicks can't interleave the conversation or duplicate tool chains.
_session_locks: dict[str, asyncio.Lock] = {}


def _lock_for(session_id: str) -> asyncio.Lock:
    return _session_locks.setdefault(session_id, asyncio.Lock())


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """Handle one farmer message and return the agent's reply + trace."""
    lock = _lock_for(req.session_id) if req.session_id else asyncio.Lock()
    async with lock:
        # Load state INSIDE the lock so a queued request sees the prior
        # request's saved messages, not a stale snapshot.
        state = store.get_or_create_session(req.session_id)
        try:
            result = await _orchestrator.run(
                state=state, message=req.message, lang=req.lang
            )
        except RuntimeError as e:  # e.g. missing OPENAI_API_KEY
            raise HTTPException(status_code=503, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
        store.save_turn(state, req.message, result)
        return result


@router.get("/sessions")
async def list_sessions() -> dict:
    """Recent sessions (persistent memory) for the session-history sidebar."""
    return {"sessions": store.list_sessions()}


@router.get("/session/{session_id}", response_model=ChatResponse)
async def get_session(session_id: str) -> ChatResponse:
    """Rehydrate a prior session (persistent memory / cross-session)."""
    return store.load_session_snapshot(session_id)
