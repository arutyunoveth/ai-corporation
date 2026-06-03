from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class SupplierProfile(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_profiles"

    supplier_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    legal_name: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    inn: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    country_code: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_supplier_profiles_status", "status"),
        Index("ix_supplier_profiles_legal_name", "legal_name"),
        Index("ix_supplier_profiles_display_name", "display_name"),
    )


class SupplierExternalRef(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_external_refs"

    supplier_id: Mapped[str] = mapped_column(String(64), ForeignKey("supplier_profiles.supplier_id"), nullable=False)
    ref_type: Mapped[str] = mapped_column(String(64), nullable=False)
    ref_value: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_supplier_external_refs_supplier_id", "supplier_id"),
        Index("ix_supplier_external_refs_ref_type", "ref_type"),
    )


class SupplierContact(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_contacts"

    supplier_id: Mapped[str] = mapped_column(String(64), ForeignKey("supplier_profiles.supplier_id"), nullable=False)
    contact_name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_supplier_contacts_supplier_id", "supplier_id"),
        Index("ix_supplier_contacts_email", "email"),
    )


class SupplierTag(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_tags"

    supplier_id: Mapped[str] = mapped_column(String(64), ForeignKey("supplier_profiles.supplier_id"), nullable=False)
    tag_code: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_supplier_tags_supplier_id", "supplier_id"),
        Index("ix_supplier_tags_tag_code", "tag_code"),
    )
