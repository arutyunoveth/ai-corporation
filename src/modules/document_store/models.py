from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.base import Base, UUIDPrimaryKeyMixin, utcnow


class DocumentArtifact(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "document_artifacts"

    artifact_ref: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    deal_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("deals.deal_id"), nullable=True)
    artifact_type: Mapped[str] = mapped_column(Text, nullable=False)
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_document_artifacts_deal_id", "deal_id"),
        Index("ix_document_artifacts_artifact_type", "artifact_type"),
    )


class ArtifactVersion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "artifact_versions"

    artifact_ref: Mapped[str] = mapped_column(String(64), ForeignKey("document_artifacts.artifact_ref"), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (UniqueConstraint("artifact_ref", "version_no", name="uq_artifact_versions_ref_version"),)


class ArtifactLink(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "artifact_links"

    artifact_ref: Mapped[str] = mapped_column(String(64), ForeignKey("document_artifacts.artifact_ref"), nullable=False)
    linked_object_type: Mapped[str] = mapped_column(Text, nullable=False)
    linked_object_ref: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_artifact_links_artifact_ref", "artifact_ref"),
        Index("ix_artifact_links_object_ref", "linked_object_type", "linked_object_ref"),
    )

