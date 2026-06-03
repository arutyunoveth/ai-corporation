from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class DashboardSnapshotSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "dashboard_snapshot_sets"

    dashboard_snapshot_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    scope_type: Mapped[str] = mapped_column(Text, nullable=False)
    scope_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    snapshot_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_dashboard_snapshot_sets_scope_type", "scope_type"),
        Index("ix_dashboard_snapshot_sets_scope_ref", "scope_ref"),
    )


class DashboardSnapshotRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "dashboard_snapshot_records"

    dashboard_snapshot_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    dashboard_snapshot_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("dashboard_snapshot_sets.dashboard_snapshot_set_id"),
        nullable=False,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_dashboard_snapshot_records_set_id", "dashboard_snapshot_set_id"),
    )


class DashboardMetricRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "dashboard_metric_records"

    dashboard_snapshot_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("dashboard_snapshot_records.dashboard_snapshot_id"),
        nullable=False,
    )
    metric_code: Mapped[str] = mapped_column(String(64), nullable=False)
    metric_value_numeric: Mapped[float | None] = mapped_column(Float, nullable=True)
    metric_value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_dashboard_metric_records_snapshot_id", "dashboard_snapshot_id"),
        Index("ix_dashboard_metric_records_metric_code", "metric_code"),
    )
