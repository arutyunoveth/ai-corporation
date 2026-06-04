from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class RequirementExtractionSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "requirement_extraction_sets"

    requirement_extraction_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    document_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("document_sets.document_set_id"),
        nullable=False,
    )
    extraction_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_requirement_extraction_sets_document_set_id", "document_set_id"),
        Index("ix_requirement_extraction_sets_status", "extraction_status"),
    )


class RequirementExtractionRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "requirement_extraction_records"

    requirement_extraction_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    requirement_extraction_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("requirement_extraction_sets.requirement_extraction_set_id"),
        nullable=False,
    )
    requirement_code: Mapped[str] = mapped_column(String(64), nullable=False)
    requirement_text: Mapped[str] = mapped_column(Text, nullable=False)
    requirement_group: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_requirement_extraction_records_set_id", "requirement_extraction_set_id"),
        Index("ix_requirement_extraction_records_requirement_code", "requirement_code"),
    )


class RequirementSourceLink(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "requirement_source_links"

    requirement_extraction_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("requirement_extraction_records.requirement_extraction_id"),
        nullable=False,
    )
    source_ref: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_requirement_source_links_requirement_extraction_id", "requirement_extraction_id"),
        Index("ix_requirement_source_links_source_ref", "source_ref"),
    )
