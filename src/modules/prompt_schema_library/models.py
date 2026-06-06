from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class PromptSchemaLibrarySet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "prompt_schema_library_sets"

    prompt_schema_library_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    library_scope: Mapped[str] = mapped_column(Text, nullable=False)
    library_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (Index("ix_prompt_schema_library_sets_library_scope", "library_scope"),)


class PromptSchemaRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "prompt_schema_records"

    prompt_schema_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    prompt_schema_library_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("prompt_schema_library_sets.prompt_schema_library_set_id"),
        nullable=False,
    )
    asset_key: Mapped[str] = mapped_column(String(128), nullable=False)
    asset_type: Mapped[str] = mapped_column(Text, nullable=False)
    version_tag: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_role: Mapped[str] = mapped_column(Text, nullable=False)
    reviewer_role: Mapped[str] = mapped_column(Text, nullable=False)
    asset_status: Mapped[str] = mapped_column(Text, nullable=False)
    usage_constraints_text: Mapped[str] = mapped_column(Text, nullable=False)
    input_schema_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_schema_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    safety_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_prompt_schema_records_set_id", "prompt_schema_library_set_id"),
        Index("ix_prompt_schema_records_asset_key", "asset_key"),
        Index("ix_prompt_schema_records_asset_status", "asset_status"),
        UniqueConstraint(
            "prompt_schema_library_set_id",
            "asset_key",
            "version_tag",
            name="uq_prompt_schema_records_set_key_version",
        ),
    )


class AgentPromptLink(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "agent_prompt_links"

    agent_registry_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("agent_registry_records.agent_registry_id"),
        nullable=False,
    )
    prompt_schema_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("prompt_schema_records.prompt_schema_id"),
        nullable=False,
    )
    link_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_agent_prompt_links_agent_registry_id", "agent_registry_id"),
        Index("ix_agent_prompt_links_prompt_schema_id", "prompt_schema_id"),
        UniqueConstraint("agent_registry_id", "prompt_schema_id", name="uq_agent_prompt_links_pair"),
    )
