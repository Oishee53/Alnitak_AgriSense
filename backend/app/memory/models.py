"""ORM models for persistent memory.

Farm 1---* Session 1---* Message
A Session also snapshots the evolving FarmProfile and any produced plan so it can
be rehydrated across app restarts (cross-session memory).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.memory.db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Farm(Base):
    __tablename__ = "farms"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    # A stable handle for the farmer (e.g. bdapps subscriberId / phone), enabling
    # cross-session recall. Nullable for anonymous demo sessions.
    owner_ref: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    profile: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    sessions: Mapped[list["Session"]] = relationship(back_populates="farm")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    farm_id: Mapped[str | None] = mapped_column(ForeignKey("farms.id"), nullable=True)
    # Latest snapshot of the collected farm profile for this conversation.
    profile_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    latest_plan: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    farm: Mapped["Farm"] = relationship(back_populates="sessions")
    messages: Mapped[list["Message"]] = relationship(back_populates="session")

    # --- convenience helpers used by the orchestrator ---
    @property
    def farm_profile(self):
        """Return the profile snapshot as a FarmProfile (imported lazily)."""
        from app.api.schemas import FarmProfile

        return FarmProfile(**(self.profile_snapshot or {}))

    def to_llm_messages(self) -> list[dict[str, Any]]:
        """Render prior messages into the LLM conversation format."""
        return [{"role": m.role, "content": m.content} for m in self.messages]


class TraceEntry(Base):
    """One persisted agent-trace step (Tier-0 #8, made durable).

    The live trace is recorded in memory for the current turn / SSE stream;
    each completed turn's steps are also persisted here so the trace panel
    survives page reloads and backend restarts.
    """

    __tablename__ = "trace_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    kind: Mapped[str] = mapped_column(String)  # thought | tool_call | tool_result | message
    tool: Mapped[str | None] = mapped_column(String, nullable=True)
    params: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    result: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Receipt(Base):
    """A persisted bdapps CaaS charge (Tier 2).

    Every checkout — success or failure — is stored so the payment history
    survives reloads/restarts and a judge can audit what was charged, to whom,
    and with which bdapps transaction id.
    """

    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    external_trx_id: Mapped[str] = mapped_column(String, index=True)
    subscriber_id: Mapped[str] = mapped_column(String)
    amount_bdt: Mapped[float] = mapped_column(Float)
    status_code: Mapped[str] = mapped_column(String)
    status_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    mode: Mapped[str] = mapped_column(String, default="sandbox")
    items: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    role: Mapped[str] = mapped_column(String)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    session: Mapped["Session"] = relationship(back_populates="messages")
