from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class ConnectorRegistrySet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "connector_registry_sets"

    connector_registry_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    scope_type: Mapped[str] = mapped_column(Text, nullable=False)
    scope_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    registry_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_connector_registry_sets_scope_type", "scope_type"),
        Index("ix_connector_registry_sets_scope_ref", "scope_ref"),
    )


class ConnectorRegistryRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "connector_registry_records"

    connector_registry_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    connector_registry_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("connector_registry_sets.connector_registry_set_id"),
        nullable=False,
    )
    connector_code: Mapped[str] = mapped_column(String(64), nullable=False)
    connector_type: Mapped[str] = mapped_column(Text, nullable=False)
    connector_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_connector_registry_records_set_id", "connector_registry_set_id"),
        Index("ix_connector_registry_records_connector_type", "connector_type"),
        Index("ix_connector_registry_records_connector_status", "connector_status"),
    )


class ConnectorSyncRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "connector_sync_runs"

    connector_sync_run_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    connector_registry_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("connector_registry_records.connector_registry_id"),
        nullable=False,
    )
    sync_status: Mapped[str] = mapped_column(Text, nullable=False)
    sync_summary: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_connector_sync_runs_connector_registry_id", "connector_registry_id"),
        Index("ix_connector_sync_runs_sync_status", "sync_status"),
    )
