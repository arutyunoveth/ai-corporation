from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.deal_registry.models import Deal
from src.modules.document_store.models import ArtifactLink, ArtifactVersion, DocumentArtifact
from src.modules.document_store.schemas import AddArtifactVersionRequest, CreateArtifactRequest, LinkArtifactRequest
from src.modules.event_log.service import append_event_record
from src.shared.db.base import utcnow
from src.shared.enums import EventSeverity
from src.shared.errors import NotFoundError
from src.shared.ids import next_artifact_ref
from src.shared.validation import require_non_empty


def _ensure_deal_exists(session: Session, deal_id: str | None) -> None:
    if not deal_id:
        return
    deal = session.scalar(select(Deal).where(Deal.deal_id == deal_id, Deal.is_deleted.is_(False)))
    if not deal:
        raise NotFoundError(f"Deal '{deal_id}' was not found")


def create_artifact(session: Session, payload: CreateArtifactRequest) -> DocumentArtifact:
    _ensure_deal_exists(session, payload.deal_id)
    artifact = DocumentArtifact(
        artifact_ref=next_artifact_ref(session, DocumentArtifact.artifact_ref),
        deal_id=payload.deal_id,
        artifact_type=payload.artifact_type,
        file_name=require_non_empty(payload.file_name, "file_name"),
        mime_type=payload.mime_type,
        storage_uri=require_non_empty(payload.storage_uri, "storage_uri"),
        checksum_sha256=payload.checksum_sha256,
        current_version=1,
    )
    session.add(artifact)
    session.flush()
    session.add(
        ArtifactVersion(
            artifact_ref=artifact.artifact_ref,
            version_no=1,
            storage_uri=artifact.storage_uri,
            checksum_sha256=artifact.checksum_sha256,
        )
    )
    append_event_record(
        session,
        deal_id=artifact.deal_id,
        event_code="artifact_created",
        source_module_id="M-003",
        severity=EventSeverity.INFO,
        payload_json={"artifact_ref": artifact.artifact_ref, "artifact_type": artifact.artifact_type},
    )
    session.commit()
    session.refresh(artifact)
    return artifact


def get_artifact(session: Session, artifact_ref: str) -> DocumentArtifact:
    artifact = session.scalar(select(DocumentArtifact).where(DocumentArtifact.artifact_ref == artifact_ref))
    if not artifact:
        raise NotFoundError(f"Artifact '{artifact_ref}' was not found")
    return artifact


def add_artifact_version(session: Session, artifact_ref: str, payload: AddArtifactVersionRequest) -> ArtifactVersion:
    artifact = get_artifact(session, artifact_ref)
    next_version = artifact.current_version + 1
    version = ArtifactVersion(
        artifact_ref=artifact.artifact_ref,
        version_no=next_version,
        storage_uri=require_non_empty(payload.storage_uri, "storage_uri"),
        checksum_sha256=payload.checksum_sha256,
    )
    session.add(version)
    artifact.current_version = next_version
    artifact.storage_uri = version.storage_uri
    artifact.checksum_sha256 = version.checksum_sha256
    artifact.updated_at = utcnow()
    session.add(artifact)
    session.flush()
    append_event_record(
        session,
        deal_id=artifact.deal_id,
        event_code="artifact_version_added",
        source_module_id="M-003",
        severity=EventSeverity.INFO,
        payload_json={"artifact_ref": artifact.artifact_ref, "version_no": next_version},
    )
    session.commit()
    session.refresh(version)
    return version


def list_artifact_versions(session: Session, artifact_ref: str) -> list[ArtifactVersion]:
    get_artifact(session, artifact_ref)
    return list(
        session.scalars(
            select(ArtifactVersion)
            .where(ArtifactVersion.artifact_ref == artifact_ref)
            .order_by(ArtifactVersion.version_no.asc())
        )
    )


def link_artifact(session: Session, artifact_ref: str, payload: LinkArtifactRequest) -> ArtifactLink:
    artifact = get_artifact(session, artifact_ref)
    link = ArtifactLink(
        artifact_ref=artifact.artifact_ref,
        linked_object_type=require_non_empty(payload.linked_object_type, "linked_object_type"),
        linked_object_ref=require_non_empty(payload.linked_object_ref, "linked_object_ref"),
    )
    session.add(link)
    session.flush()
    append_event_record(
        session,
        deal_id=artifact.deal_id,
        event_code="artifact_linked",
        source_module_id="M-003",
        severity=EventSeverity.INFO,
        payload_json={
            "artifact_ref": artifact.artifact_ref,
            "linked_object_type": link.linked_object_type,
            "linked_object_ref": link.linked_object_ref,
        },
    )
    session.commit()
    session.refresh(link)
    return link

