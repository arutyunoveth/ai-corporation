from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class ActionQueueSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "action_queue_sets"

    action_queue_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    scope_type: Mapped[str] = mapped_column(Text, nullable=False)
    scope_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    queue_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_action_queue_sets_scope_type", "scope_type"),
        Index("ix_action_queue_sets_scope_ref", "scope_ref"),
    )


class ActionQueueRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "action_queue_records"

    action_queue_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    action_queue_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("action_queue_sets.action_queue_set_id"),
        nullable=False,
    )
    action_code: Mapped[str] = mapped_column(String(64), nullable=False)
    action_type: Mapped[str] = mapped_column(Text, nullable=False)
    action_status: Mapped[str] = mapped_column(Text, nullable=False)
    action_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_action_queue_records_set_id", "action_queue_set_id"),
        Index("ix_action_queue_records_action_type", "action_type"),
        Index("ix_action_queue_records_action_status", "action_status"),
    )


class ActionQueueApproval(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "action_queue_approvals"

    action_queue_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("action_queue_records.action_queue_id"),
        nullable=False,
    )
    approval_status: Mapped[str] = mapped_column(Text, nullable=False)
    approved_by_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_action_queue_approvals_action_queue_id", "action_queue_id"),
        Index("ix_action_queue_approvals_approval_status", "approval_status"),
    )
