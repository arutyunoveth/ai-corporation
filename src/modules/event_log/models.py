from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class EventRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "event_records"

    event_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=True)
    event_code: Mapped[str] = mapped_column(Text, nullable=False)
    source_module_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_agent_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_event_records_deal_id", "deal_id"),
        Index("ix_event_records_event_code", "event_code"),
        Index("ix_event_records_source_module_id", "source_module_id"),
        Index("ix_event_records_created_at", "created_at"),
    )


class DecisionRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "decision_records"

    decision_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    decision_code: Mapped[str] = mapped_column(Text, nullable=False)
    decided_by_type: Mapped[str] = mapped_column(Text, nullable=False)
    decided_by_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_decision_records_deal_id", "deal_id"),
        Index("ix_decision_records_decision_code", "decision_code"),
    )

