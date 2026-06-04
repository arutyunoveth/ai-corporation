from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class VendorConnectorSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "vendor_connector_sets"

    vendor_connector_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    scope_type: Mapped[str] = mapped_column(Text, nullable=False)
    scope_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    profile_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_vendor_connector_sets_scope_type", "scope_type"),
        Index("ix_vendor_connector_sets_scope_ref", "scope_ref"),
    )


class VendorConnectorRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "vendor_connector_records"

    vendor_connector_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    vendor_connector_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("vendor_connector_sets.vendor_connector_set_id"),
        nullable=False,
    )
    connector_registry_id: Mapped[str] = mapped_column(String(64), nullable=False)
    vendor_code: Mapped[str] = mapped_column(String(64), nullable=False)
    vendor_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_vendor_connector_records_set_id", "vendor_connector_set_id"),
        Index("ix_vendor_connector_records_connector_registry_id", "connector_registry_id"),
        Index("ix_vendor_connector_records_vendor_status", "vendor_status"),
    )


class VendorConnectorCapability(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "vendor_connector_capabilities"

    vendor_connector_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("vendor_connector_records.vendor_connector_id"),
        nullable=False,
    )
    capability_code: Mapped[str] = mapped_column(String(64), nullable=False)
    capability_status: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_vendor_connector_capabilities_vendor_connector_id", "vendor_connector_id"),
        Index("ix_vendor_connector_capabilities_capability_status", "capability_status"),
    )
