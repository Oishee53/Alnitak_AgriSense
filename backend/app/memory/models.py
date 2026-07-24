"""ORM models for persistent memory.

Farm 1---* Session 1---* Message
A Session also snapshots the evolving FarmProfile and any produced plan so it can
be rehydrated across app restarts (cross-session memory).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
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


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    role: Mapped[str] = mapped_column(String)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    session: Mapped["Session"] = relationship(back_populates="messages")
