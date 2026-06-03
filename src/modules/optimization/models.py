from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class OptimizationRecommendationSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "optimization_recommendation_sets"

    optimization_recommendation_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    scope_type: Mapped[str] = mapped_column(Text, nullable=False)
    scope_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    optimization_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_optimization_recommendation_sets_scope_type", "scope_type"),
        Index("ix_optimization_recommendation_sets_scope_ref", "scope_ref"),
    )


class OptimizationRecommendationRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "optimization_recommendation_records"

    optimization_recommendation_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    optimization_recommendation_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("optimization_recommendation_sets.optimization_recommendation_set_id"),
        nullable=False,
    )
    recommendation_code: Mapped[str] = mapped_column(String(64), nullable=False)
    recommendation_type: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_optimization_recommendation_records_set_id", "optimization_recommendation_set_id"),
        Index("ix_optimization_recommendation_records_type", "recommendation_type"),
    )


class OptimizationSignalRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "optimization_signal_records"

    optimization_recommendation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("optimization_recommendation_records.optimization_recommendation_id"),
        nullable=False,
    )
    signal_code: Mapped[str] = mapped_column(String(64), nullable=False)
    signal_value_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_optimization_signal_records_recommendation_id", "optimization_recommendation_id"),
        Index("ix_optimization_signal_records_signal_code", "signal_code"),
    )
