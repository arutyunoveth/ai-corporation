from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class LearningAutomationSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "learning_automation_sets"

    learning_automation_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    scope_type: Mapped[str] = mapped_column(Text, nullable=False)
    scope_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    automation_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_learning_automation_sets_scope_type", "scope_type"),
        Index("ix_learning_automation_sets_scope_ref", "scope_ref"),
    )


class LearningAutomationRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "learning_automation_records"

    learning_automation_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    learning_automation_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("learning_automation_sets.learning_automation_set_id"),
        nullable=False,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_learning_automation_records_set_id", "learning_automation_set_id"),
    )


class LearningRecommendationRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "learning_recommendation_records"

    learning_automation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("learning_automation_records.learning_automation_id"),
        nullable=False,
    )
    recommendation_code: Mapped[str] = mapped_column(String(64), nullable=False)
    recommendation_type: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_learning_recommendation_records_automation_id", "learning_automation_id"),
        Index("ix_learning_recommendation_records_type", "recommendation_type"),
    )
