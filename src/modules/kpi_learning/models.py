from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class KPILearningSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "kpi_learning_sets"

    kpi_learning_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    deal_closure_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("deal_closure_sets.deal_closure_set_id"),
        nullable=False,
    )
    kpi_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_kpi_learning_sets_deal_id", "deal_id"),
        Index("ix_kpi_learning_sets_deal_closure_set_id", "deal_closure_set_id"),
    )


class KPILearningRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "kpi_learning_records"

    kpi_learning_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    kpi_learning_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("kpi_learning_sets.kpi_learning_set_id"),
        nullable=False,
    )
    cycle_time_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    margin_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    supplier_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    incident_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payment_collection_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_kpi_learning_records_set_id", "kpi_learning_set_id"),
    )


class LearningNoteRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "learning_note_records"

    learning_note_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    kpi_learning_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("kpi_learning_records.kpi_learning_id"),
        nullable=False,
    )
    note_type: Mapped[str] = mapped_column(Text, nullable=False)
    note_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_learning_note_records_kpi_learning_id", "kpi_learning_id"),
        Index("ix_learning_note_records_note_type", "note_type"),
    )
