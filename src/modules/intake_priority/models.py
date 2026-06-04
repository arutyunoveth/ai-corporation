from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class IntakePrioritySet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "intake_priority_sets"

    intake_priority_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    prioritization_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_intake_priority_sets_deal_id", "deal_id"),
        Index("ix_intake_priority_sets_status", "prioritization_status"),
    )


class IntakePriorityRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "intake_priority_records"

    intake_priority_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    intake_priority_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("intake_priority_sets.intake_priority_set_id"),
        nullable=False,
    )
    priority_score: Mapped[float] = mapped_column(Float, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_queue_position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_intake_priority_records_set_id", "intake_priority_set_id"),
        Index("ix_intake_priority_records_priority_score", "priority_score"),
    )


class IntakePriorityFactor(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "intake_priority_factors"

    intake_priority_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("intake_priority_records.intake_priority_id"),
        nullable=False,
    )
    factor_code: Mapped[str] = mapped_column(String(64), nullable=False)
    factor_value: Mapped[float] = mapped_column(Float, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_intake_priority_factors_intake_priority_id", "intake_priority_id"),
        Index("ix_intake_priority_factors_factor_code", "factor_code"),
    )
