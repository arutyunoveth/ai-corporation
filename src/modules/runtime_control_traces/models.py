from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class RuntimeControlTrace(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "runtime_control_traces"

    runtime_trace_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    runtime_slice: Mapped[str] = mapped_column(Text, nullable=False)
    source_entity: Mapped[str] = mapped_column(Text, nullable=False)
    actor_type: Mapped[str] = mapped_column(Text, nullable=False)
    actor_ref: Mapped[str] = mapped_column(Text, nullable=False)
    action_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_module: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_record_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_schema_ref: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("prompt_schema_records.prompt_schema_id"),
        nullable=True,
    )
    agent_profile_ref: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("agent_registry_records.agent_registry_id"),
        nullable=True,
    )
    input_artifact_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_artifact_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_status: Mapped[str] = mapped_column(Text, nullable=False)
    human_review_status: Mapped[str] = mapped_column(Text, nullable=False)
    reviewer_operator: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_disposition: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_runtime_control_traces_runtime_slice", "runtime_slice"),
        Index("ix_runtime_control_traces_action_type", "action_type"),
        Index("ix_runtime_control_traces_prompt_schema_ref", "prompt_schema_ref"),
        Index("ix_runtime_control_traces_agent_profile_ref", "agent_profile_ref"),
        Index("ix_runtime_control_traces_human_review_status", "human_review_status"),
    )
