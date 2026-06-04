from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class IntegrationTaskSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "integration_task_sets"

    integration_task_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    scope_type: Mapped[str] = mapped_column(Text, nullable=False)
    scope_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    task_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_integration_task_sets_scope_type", "scope_type"),
        Index("ix_integration_task_sets_scope_ref", "scope_ref"),
    )


class IntegrationTaskRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "integration_task_records"

    integration_task_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    integration_task_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("integration_task_sets.integration_task_set_id"),
        nullable=False,
    )
    connector_registry_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action_queue_id: Mapped[str] = mapped_column(String(64), nullable=False)
    task_type: Mapped[str] = mapped_column(Text, nullable=False)
    task_payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_integration_task_records_set_id", "integration_task_set_id"),
        Index("ix_integration_task_records_connector_registry_id", "connector_registry_id"),
        Index("ix_integration_task_records_action_queue_id", "action_queue_id"),
        Index("ix_integration_task_records_task_type", "task_type"),
    )


class IntegrationTaskBinding(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "integration_task_bindings"

    integration_task_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("integration_task_records.integration_task_id"),
        nullable=False,
    )
    source_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    binding_type: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_integration_task_bindings_integration_task_id", "integration_task_id"),
        Index("ix_integration_task_bindings_binding_type", "binding_type"),
    )
