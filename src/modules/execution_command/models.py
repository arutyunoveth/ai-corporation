from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class ExecutionCommandSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "execution_command_sets"

    execution_command_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    delivery_launch_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("delivery_launch_sets.delivery_launch_set_id"),
        nullable=False,
    )
    execution_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_execution_command_sets_deal_id", "deal_id"),
        Index("ix_execution_command_sets_delivery_launch_set_id", "delivery_launch_set_id"),
    )


class ExecutionCommandRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "execution_command_records"

    execution_command_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    execution_command_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("execution_command_sets.execution_command_set_id"),
        nullable=False,
    )
    current_phase: Mapped[str] = mapped_column(Text, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_execution_command_records_set_id", "execution_command_set_id"),
    )


class ExecutionCommandBinding(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "execution_command_bindings"

    execution_command_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("execution_command_sets.execution_command_set_id"),
        nullable=False,
    )
    source_object_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_object_ref: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_execution_command_bindings_execution_command_set_id", "execution_command_set_id"),
        Index("ix_execution_command_bindings_source_object_ref", "source_object_ref"),
    )
