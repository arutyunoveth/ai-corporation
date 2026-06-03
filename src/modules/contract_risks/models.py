from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class ContractRiskSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "contract_risk_sets"

    contract_risk_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    document_set_id: Mapped[str] = mapped_column(String(64), ForeignKey("document_sets.document_set_id"), nullable=False)
    risk_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_contract_risk_sets_deal_id", "deal_id"),
        Index("ix_contract_risk_sets_document_set_id", "document_set_id"),
    )


class ContractRiskRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "contract_risk_records"

    contract_risk_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    contract_risk_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("contract_risk_sets.contract_risk_set_id"),
        nullable=False,
    )
    source_artifact_ref: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("document_artifacts.artifact_ref"),
        nullable=True,
    )
    clause_type: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_contract_risk_records_set_id", "contract_risk_set_id"),
        Index("ix_contract_risk_records_source_artifact_ref", "source_artifact_ref"),
        Index("ix_contract_risk_records_clause_type", "clause_type"),
    )


class ContractRiskFlag(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "contract_risk_flags"

    contract_risk_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("contract_risk_records.contract_risk_id"),
        nullable=False,
    )
    flag_code: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_contract_risk_flags_contract_risk_id", "contract_risk_id"),
        Index("ix_contract_risk_flags_severity", "severity"),
    )
