from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class PostmortemSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "postmortem_sets"

    postmortem_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    deal_closure_report_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("deal_closure_report_sets.deal_closure_report_set_id"),
        nullable=False,
    )
    incident_register_set_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("incident_register_sets.incident_register_set_id"),
        nullable=True,
    )
    claim_trigger_set_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("claim_trigger_sets.claim_trigger_set_id"),
        nullable=True,
    )
    kpi_learning_set_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("kpi_learning_sets.kpi_learning_set_id"),
        nullable=True,
    )
    postmortem_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_postmortem_sets_deal_id", "deal_id"),
        Index("ix_postmortem_sets_report_set_id", "deal_closure_report_set_id"),
    )


class PostmortemRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "postmortem_records"

    postmortem_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    postmortem_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("postmortem_sets.postmortem_set_id"),
        nullable=False,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause_summary: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation_summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_postmortem_records_set_id", "postmortem_set_id"),
    )


class PostmortemFinding(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "postmortem_findings"

    postmortem_id: Mapped[str] = mapped_column(String(64), ForeignKey("postmortem_records.postmortem_id"), nullable=False)
    finding_code: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_postmortem_findings_postmortem_id", "postmortem_id"),
        Index("ix_postmortem_findings_finding_code", "finding_code"),
    )


class PostmortemActionItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "postmortem_action_items"

    postmortem_id: Mapped[str] = mapped_column(String(64), ForeignKey("postmortem_records.postmortem_id"), nullable=False)
    action_code: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    action_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_postmortem_action_items_postmortem_id", "postmortem_id"),
        Index("ix_postmortem_action_items_action_code", "action_code"),
    )
