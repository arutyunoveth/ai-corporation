from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class DealClosureReportSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "deal_closure_report_sets"

    deal_closure_report_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    deal_closure_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("deal_closure_sets.deal_closure_set_id"),
        nullable=False,
    )
    acceptance_control_set_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("acceptance_control_sets.acceptance_control_set_id"),
        nullable=True,
    )
    closing_docs_set_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("closing_docs_sets.closing_docs_set_id"),
        nullable=True,
    )
    payment_tracking_set_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("payment_tracking_sets.payment_tracking_set_id"),
        nullable=True,
    )
    claim_trigger_set_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("claim_trigger_sets.claim_trigger_set_id"),
        nullable=True,
    )
    report_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_deal_closure_report_sets_deal_id", "deal_id"),
        Index("ix_deal_closure_report_sets_closure_set_id", "deal_closure_set_id"),
    )


class DealClosureReportRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "deal_closure_report_records"

    deal_closure_report_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_closure_report_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("deal_closure_report_sets.deal_closure_report_set_id"),
        nullable=False,
    )
    report_code: Mapped[str] = mapped_column(String(64), nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    closure_health: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_deal_closure_report_records_set_id", "deal_closure_report_set_id"),
        Index("ix_deal_closure_report_records_report_code", "report_code"),
    )


class DealClosureReportLink(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "deal_closure_report_links"

    deal_closure_report_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("deal_closure_report_records.deal_closure_report_id"),
        nullable=False,
    )
    source_ref: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_deal_closure_report_links_report_id", "deal_closure_report_id"),
    )
