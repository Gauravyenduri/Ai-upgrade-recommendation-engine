"""SQLAlchemy ORM models for persistence and the retrieval knowledge base."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import String, Float, Integer, DateTime, Boolean, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


class StoredRecommendation(Base):
    """Persisted recommendation + its human-review lifecycle."""
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    resource_id: Mapped[str] = mapped_column(String(255), index=True)
    recommended_strategy: Mapped[str] = mapped_column(String(32))
    risk_score: Mapped[float] = mapped_column(Float)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=False)
    review_status: Mapped[str] = mapped_column(String(32), default="PENDING")
    reviewer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[str] = mapped_column(Text)
    factors: Mapped[str] = mapped_column(Text)  # JSON-encoded list
    generated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=lambda: dt.datetime.now(dt.timezone.utc)
    )


class UpgradeOutcome(Base):
    """Historical upgrade outcomes — the corpus the retrieval pipeline searches."""
    __tablename__ = "upgrade_outcomes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    resource_type: Mapped[str] = mapped_column(String(64), index=True)
    from_version: Mapped[str] = mapped_column(String(64))
    to_version: Mapped[str] = mapped_column(String(64))
    strategy: Mapped[str] = mapped_column(String(32))
    criticality: Mapped[str] = mapped_column(String(16))
    succeeded: Mapped[bool] = mapped_column(Boolean)
    rollback_required: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
