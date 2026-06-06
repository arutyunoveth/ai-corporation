from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class RuntimeMetadataSlice(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "runtime_metadata_slices"

    runtime_metadata_slice_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    runtime_slice: Mapped[str] = mapped_column(Text, nullable=False)
    linked_agent_profile_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("agent_registry_records.agent_registry_id"),
        nullable=False,
    )
    linked_prompt_schema_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("prompt_schema_records.prompt_schema_id"),
        nullable=False,
    )
    allowed_runtime_contexts: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    forbidden_runtime_contexts: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    review_status: Mapped[str] = mapped_column(Text, nullable=False)
    trace_refs_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_runtime_metadata_slices_runtime_slice", "runtime_slice"),
        Index("ix_runtime_metadata_slices_agent_profile", "linked_agent_profile_id"),
        Index("ix_runtime_metadata_slices_prompt_schema", "linked_prompt_schema_id"),
        Index("ix_runtime_metadata_slices_review_status", "review_status"),
    )
