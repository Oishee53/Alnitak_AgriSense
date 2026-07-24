"""Memory CRUD — persistent session state over SQLite.

The orchestrator works with a plain `SessionState` (no live ORM objects
escaping the DB session), which keeps the agent loop simple and makes
cross-session persistence (Tier 1) free: state is rebuilt from the DB on every
request, so a browser refresh or app restart never loses the farm profile.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from app.api.schemas import ChatResponse, FarmProfile
from app.memory.db import SessionLocal
from app.memory.models import Message, Session


@dataclass
class SessionState:
    id: str
    profile: dict[str, Any] = field(default_factory=dict)
    history: list[dict[str, str]] = field(default_factory=list)  # [{role, content}]
    artifacts: dict[str, Any] = field(default_factory=dict)  # crop_options / season_plan / financials

    def farm_profile(self) -> FarmProfile:
        return FarmProfile(**{k: v for k, v in self.profile.items() if v is not None})

    def missing_fields(self) -> list[str]:
        return self.farm_profile().missing_fields()


def get_or_create_session(session_id: str | None) -> SessionState:
    """Return an existing session (with history) or create a fresh one."""
    with SessionLocal() as db:
        if session_id:
            row = db.get(Session, session_id)
            if row is not None:
                msgs = (
                    db.query(Message)
                    .filter(Message.session_id == row.id)
                    .order_by(Message.created_at, Message.id)
                    .all()
                )
                return SessionState(
                    id=row.id,
                    profile=dict(row.profile_snapshot or {}),
                    history=[{"role": m.role, "content": m.content} for m in msgs],
                    artifacts=dict(row.latest_plan or {}),
                )
        # create new
        new_id = session_id or uuid.uuid4().hex
        row = Session(id=new_id, profile_snapshot={}, latest_plan={})
        db.add(row)
        db.commit()
        return SessionState(id=new_id)


def save_turn(state: SessionState, user_message: str, result: ChatResponse) -> None:
    """Persist the turn: both messages + profile snapshot + latest artifacts."""
    with SessionLocal() as db:
        row = db.get(Session, state.id)
        if row is None:  # defensive: recreate if somehow missing
            row = Session(id=state.id)
            db.add(row)
        row.profile_snapshot = dict(state.profile)
        row.latest_plan = dict(state.artifacts)
        db.add(Message(session_id=state.id, role="user", content=user_message))
        if result.reply:
            db.add(Message(session_id=state.id, role="assistant", content=result.reply))
        db.commit()


def load_session_snapshot(session_id: str) -> ChatResponse:
    """Rehydrate a prior session (GET /api/session/{id}) — memory across
    sessions: profile, chat history, and the latest plan artifacts."""
    state = get_or_create_session(session_id)
    arts = state.artifacts or {}
    return ChatResponse(
        session_id=state.id,
        reply="",
        farm=state.farm_profile(),
        trace=[],
        history=state.history,
        crop_options=arts.get("crop_options"),
        season_plan=arts.get("season_plan"),
        financials=arts.get("financials"),
    )
