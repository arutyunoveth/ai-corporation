from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class ClaimTriggerSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "claim_trigger_sets"

    claim_trigger_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    trigger_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (Index("ix_claim_trigger_sets_deal_id", "deal_id"),)


class ClaimTriggerRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "claim_trigger_records"

    claim_trigger_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    claim_trigger_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("claim_trigger_sets.claim_trigger_set_id"),
        nullable=False,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    trigger_reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (Index("ix_claim_trigger_records_set_id", "claim_trigger_set_id"),)


class ClaimTriggerFlag(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "claim_trigger_flags"

    claim_trigger_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("claim_trigger_records.claim_trigger_id"),
        nullable=False,
    )
    flag_code: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_claim_trigger_flags_trigger_id", "claim_trigger_id"),
        Index("ix_claim_trigger_flags_flag_code", "flag_code"),
    )


class ClaimTriggerLink(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "claim_trigger_links"

    claim_trigger_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("claim_trigger_records.claim_trigger_id"),
        nullable=False,
    )
    source_ref: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (Index("ix_claim_trigger_links_trigger_id", "claim_trigger_id"),)
