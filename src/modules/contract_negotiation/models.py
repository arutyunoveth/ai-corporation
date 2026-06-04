from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class ContractNegotiationSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "contract_negotiation_sets"

    contract_negotiation_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    negotiation_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_contract_negotiation_sets_deal_id", "deal_id"),
        Index("ix_contract_negotiation_sets_status", "negotiation_status"),
    )


class ContractNegotiationRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "contract_negotiation_records"

    contract_negotiation_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    contract_negotiation_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("contract_negotiation_sets.contract_negotiation_set_id"),
        nullable=False,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    negotiation_pack_manifest_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_contract_negotiation_records_set_id", "contract_negotiation_set_id"),
    )


class ContractNegotiationIssue(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "contract_negotiation_issues"

    contract_negotiation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("contract_negotiation_records.contract_negotiation_id"),
        nullable=False,
    )
    issue_code: Mapped[str] = mapped_column(String(64), nullable=False)
    issue_text: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_contract_negotiation_issues_contract_negotiation_id", "contract_negotiation_id"),
        Index("ix_contract_negotiation_issues_severity", "severity"),
    )


class ContractNegotiationComment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "contract_negotiation_comments"

    contract_negotiation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("contract_negotiation_records.contract_negotiation_id"),
        nullable=False,
    )
    clause_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_contract_negotiation_comments_contract_negotiation_id", "contract_negotiation_id"),
        Index("ix_contract_negotiation_comments_clause_ref", "clause_ref"),
    )
