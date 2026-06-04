from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class OperatorSessionSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "operator_session_sets"

    operator_session_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    scope_type: Mapped[str] = mapped_column(Text, nullable=False)
    scope_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    session_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_operator_session_sets_scope_type", "scope_type"),
        Index("ix_operator_session_sets_scope_ref", "scope_ref"),
    )


class OperatorSessionRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "operator_session_records"

    operator_session_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    operator_session_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("operator_session_sets.operator_session_set_id"),
        nullable=False,
    )
    opened_by_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_operator_session_records_set_id", "operator_session_set_id"),
    )


class OperatorSessionItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "operator_session_items"

    operator_session_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("operator_session_records.operator_session_id"),
        nullable=False,
    )
    item_code: Mapped[str] = mapped_column(String(64), nullable=False)
    item_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    item_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_operator_session_items_operator_session_id", "operator_session_id"),
        Index("ix_operator_session_items_item_type", "item_type"),
        Index("ix_operator_session_items_item_status", "item_status"),
    )
