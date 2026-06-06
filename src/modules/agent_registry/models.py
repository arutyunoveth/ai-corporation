from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class AgentRegistrySet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "agent_registry_sets"

    agent_registry_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    registry_scope: Mapped[str] = mapped_column(Text, nullable=False)
    registry_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (Index("ix_agent_registry_sets_registry_scope", "registry_scope"),)


class AgentRegistryRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "agent_registry_records"

    agent_registry_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    agent_registry_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("agent_registry_sets.agent_registry_set_id"),
        nullable=False,
    )
    agent_key: Mapped[str] = mapped_column(String(128), nullable=False)
    agent_label: Mapped[str] = mapped_column(Text, nullable=False)
    owner_role: Mapped[str] = mapped_column(Text, nullable=False)
    reviewer_role: Mapped[str] = mapped_column(Text, nullable=False)
    activation_state: Mapped[str] = mapped_column(Text, nullable=False)
    approval_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    allowed_capabilities_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    blocked_capabilities_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_agent_registry_records_set_id", "agent_registry_set_id"),
        Index("ix_agent_registry_records_agent_key", "agent_key"),
        Index("ix_agent_registry_records_activation_state", "activation_state"),
        UniqueConstraint("agent_registry_set_id", "agent_key", name="uq_agent_registry_records_set_key"),
    )
