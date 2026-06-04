from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class BidCompletenessSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "bid_completeness_sets"

    bid_completeness_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    bid_package_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("bid_package_sets.bid_package_set_id"),
        nullable=False,
    )
    completeness_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_bid_completeness_sets_deal_id", "deal_id"),
        Index("ix_bid_completeness_sets_package_set_id", "bid_package_set_id"),
    )


class BidCompletenessRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "bid_completeness_records"

    bid_completeness_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    bid_completeness_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("bid_completeness_sets.bid_completeness_set_id"),
        nullable=False,
    )
    mandatory_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mandatory_present: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    optional_present: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_bid_completeness_records_set_id", "bid_completeness_set_id"),
    )


class BidCompletenessFlag(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "bid_completeness_flags"

    bid_completeness_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("bid_completeness_records.bid_completeness_id"),
        nullable=False,
    )
    flag_code: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_bid_completeness_flags_completeness_id", "bid_completeness_id"),
        Index("ix_bid_completeness_flags_severity", "severity"),
    )


class BidReadinessReport(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "bid_readiness_reports"

    bid_readiness_report_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    bid_completeness_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("bid_completeness_sets.bid_completeness_set_id"),
        nullable=False,
    )
    readiness_summary: Mapped[str] = mapped_column(Text, nullable=False)
    blocking_issue_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_bid_readiness_reports_set_id", "bid_completeness_set_id"),
    )
