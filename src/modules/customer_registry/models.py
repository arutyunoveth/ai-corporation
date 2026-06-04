from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class CustomerProfile(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "customer_profiles"

    customer_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    legal_name: Mapped[str] = mapped_column(Text, nullable=False)
    inn: Mapped[str | None] = mapped_column(String(32), nullable=True)
    kpp: Mapped[str | None] = mapped_column(String(32), nullable=True)
    customer_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_customer_profiles_inn", "inn"),
        Index("ix_customer_profiles_legal_name", "legal_name"),
        Index("ix_customer_profiles_customer_status", "customer_status"),
    )


class CustomerExternalRef(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "customer_external_refs"

    customer_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("customer_profiles.customer_id"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_customer_external_refs_customer_id", "customer_id"),
        Index("ix_customer_external_refs_source_type", "source_type"),
    )


class CustomerContour(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "customer_contours"

    customer_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("customer_profiles.customer_id"),
        nullable=False,
    )
    contour_code: Mapped[str] = mapped_column(String(64), nullable=False)
    contour_name: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_customer_contours_customer_id", "customer_id"),
        Index("ix_customer_contours_contour_code", "contour_code"),
    )
