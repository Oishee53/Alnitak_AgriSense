"""Memory CRUD — persistent session state over SQLite.

The orchestrator works with a plain `SessionState` (no live ORM objects
escaping the DB session), which keeps the agent loop simple and makes
cross-session persistence (Tier 1) free: state is rebuilt from the DB on every
request, so a browser refresh or app restart never loses the farm profile.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.api.schemas import ChatResponse, FarmProfile
from app.memory.db import SessionLocal
from app.memory.models import Message, Receipt, Session, TraceEntry


def _jsonable(value: Any) -> Any:
    """Coerce a value into something a JSON column can store."""
    if value is None:
        return None
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
    except Exception:
        return str(value)


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
        # Persist this turn's trace steps so the trace panel survives page
        # reloads and backend restarts (the live trace is in-memory only).
        for s in result.trace:
            db.add(
                TraceEntry(
                    session_id=state.id,
                    kind=s.kind,
                    tool=s.tool,
                    params=_jsonable(s.params),
                    result=_jsonable(s.result),
                    summary=s.summary,
                )
            )
        db.commit()


def persist_artifacts(state: SessionState) -> None:
    """Persist just the current artifacts snapshot (no new chat messages).

    Used by out-of-band producers like the photo-diagnosis endpoint, which add
    an artifact without a full chat turn.
    """
    with SessionLocal() as db:
        row = db.get(Session, state.id)
        if row is None:
            row = Session(id=state.id)
            db.add(row)
        row.profile_snapshot = dict(state.profile)
        row.latest_plan = dict(state.artifacts)
        db.commit()


def load_trace(session_id: str) -> list[dict[str, Any]]:
    """Return the persisted trace for a session (renumbered sequentially)."""
    with SessionLocal() as db:
        rows = (
            db.query(TraceEntry)
            .filter(TraceEntry.session_id == session_id)
            .order_by(TraceEntry.id)
            .all()
        )
        return [
            {
                "step": i + 1,
                "kind": r.kind,
                "tool": r.tool,
                "params": r.params,
                "result": r.result,
                "summary": r.summary,
            }
            for i, r in enumerate(rows)
        ]


def save_receipt(
    session_id: str,
    resp: "ChatResponse | Any",
    trace_steps: list[dict[str, Any]] | None = None,
) -> None:
    """Persist a bdapps CaaS charge and its trace steps.

    `resp` is a CheckoutResponse. The trace steps (the CaaS request + response)
    are stored as TraceEntry rows so the payment shows up in the agent trace
    even after a reload.
    """
    with SessionLocal() as db:
        # Ensure the session row exists (a demo may pay before chatting).
        if db.get(Session, session_id) is None:
            db.add(Session(id=session_id, profile_snapshot={}, latest_plan={}))
        r = resp.receipt or {}
        db.add(
            Receipt(
                session_id=session_id,
                external_trx_id=resp.external_trx_id,
                subscriber_id=resp.receipt.get("subscriber_id", ""),
                amount_bdt=resp.amount_bdt,
                status_code=resp.status_code,
                status_detail=resp.status_detail,
                success=resp.success,
                mode=r.get("mode", "sandbox"),
                items=_jsonable(r.get("items")),
            )
        )
        for s in trace_steps or []:
            db.add(
                TraceEntry(
                    session_id=session_id,
                    kind=s.get("kind", "tool_call"),
                    tool=s.get("tool"),
                    params=_jsonable(s.get("params")),
                    result=_jsonable(s.get("result")),
                    summary=s.get("summary"),
                )
            )
        db.commit()


def list_receipts(session_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Return this session's payment history, newest first."""
    with SessionLocal() as db:
        rows = (
            db.query(Receipt)
            .filter(Receipt.session_id == session_id)
            .order_by(Receipt.created_at.desc(), Receipt.id.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "external_trx_id": r.external_trx_id,
                "subscriber_id": r.subscriber_id,
                "amount_bdt": r.amount_bdt,
                "status_code": r.status_code,
                "status_detail": r.status_detail,
                "success": r.success,
                "mode": r.mode,
                "items": r.items,
                "paid_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]


def list_sessions(limit: int = 30) -> list[dict[str, Any]]:
    """Recent sessions with a human label — for the session-history sidebar.

    Sessions with no messages (created but never chatted in) are skipped.
    """
    with SessionLocal() as db:
        rows = (
            db.query(Session).order_by(Session.created_at.desc()).limit(200).all()
        )
        out: list[dict[str, Any]] = []
        for row in rows:
            first_msg = (
                db.query(Message)
                .filter(Message.session_id == row.id, Message.role == "user")
                .order_by(Message.created_at, Message.id)
                .first()
            )
            if first_msg is None:
                continue  # empty shell session — not worth listing
            msg_count = (
                db.query(Message).filter(Message.session_id == row.id).count()
            )
            prof = row.profile_snapshot or {}
            arts = row.latest_plan or {}
            crop = (arts.get("season_plan") or {}).get("crop") or (
                arts.get("financials") or {}
            ).get("crop")
            bits = [b for b in [prof.get("location"), prof.get("target_season"), crop] if b]
            label = " · ".join(bits) if bits else first_msg.content[:60]
            out.append(
                {
                    "id": row.id,
                    "label": label,
                    "preview": first_msg.content[:90],
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "message_count": msg_count,
                }
            )
            if len(out) >= limit:
                break
        return out


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
        fertilizer_schedule=arts.get("fertilizer_schedule"),
        pest_risk=arts.get("pest_risk"),
        scenario=arts.get("scenario"),
        weather_alerts=arts.get("weather_alerts"),
        market=arts.get("market"),
        suppliers=arts.get("suppliers"),
        disease=arts.get("disease"),
    )
