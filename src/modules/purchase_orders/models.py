from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class PurchaseOrderSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "purchase_order_sets"

    purchase_order_set_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=False)
    supplier_id: Mapped[str] = mapped_column(String(64), ForeignKey("supplier_profiles.supplier_id"), nullable=False)
    po_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_purchase_order_sets_deal_id", "deal_id"),
        Index("ix_purchase_order_sets_supplier_id", "supplier_id"),
    )


class PurchaseOrderRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "purchase_order_records"

    purchase_order_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    purchase_order_set_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("purchase_order_sets.purchase_order_set_id"),
        nullable=False,
    )
    po_number: Mapped[str] = mapped_column(String(64), nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_purchase_order_records_set_id", "purchase_order_set_id"),
        Index("ix_purchase_order_records_po_number", "po_number"),
    )


class PurchaseOrderItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "purchase_order_items"

    purchase_order_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("purchase_order_records.purchase_order_id"),
        nullable=False,
    )
    item_code: Mapped[str] = mapped_column(String(64), nullable=False)
    item_description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_purchase_order_items_purchase_order_id", "purchase_order_id"),
        Index("ix_purchase_order_items_item_code", "item_code"),
    )


class PurchaseOrderLink(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "purchase_order_links"

    purchase_order_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("purchase_order_records.purchase_order_id"),
        nullable=False,
    )
    source_ref: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_purchase_order_links_purchase_order_id", "purchase_order_id"),
    )
