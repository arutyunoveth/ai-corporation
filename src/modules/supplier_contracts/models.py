from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class SupplierContractSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_contract_sets"

    supplier_contract_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    supplier_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("supplier_profiles.supplier_id"),
        nullable=False,
    )
    contract_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_supplier_contract_sets_deal_id", "deal_id"),
        Index("ix_supplier_contract_sets_supplier_id", "supplier_id"),
    )


class SupplierContractRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_contract_records"

    supplier_contract_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    supplier_contract_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("supplier_contract_sets.supplier_contract_set_id"),
        nullable=False,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    contract_manifest_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_supplier_contract_records_set_id", "supplier_contract_set_id"),
    )


class SupplierContractObligation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_contract_obligations"

    supplier_contract_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("supplier_contract_records.supplier_contract_id"),
        nullable=False,
    )
    obligation_code: Mapped[str] = mapped_column(String(64), nullable=False)
    obligation_text: Mapped[str] = mapped_column(Text, nullable=False)
    obligation_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_supplier_contract_obligations_contract_id", "supplier_contract_id"),
        Index("ix_supplier_contract_obligations_obligation_code", "obligation_code"),
    )


class SupplierContractComment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "supplier_contract_comments"

    supplier_contract_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("supplier_contract_records.supplier_contract_id"),
        nullable=False,
    )
    clause_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_supplier_contract_comments_contract_id", "supplier_contract_id"),
        Index("ix_supplier_contract_comments_clause_ref", "clause_ref"),
    )
