from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.document_ingestion.service import get_document_set
from src.modules.event_log.service import append_event_record
from src.modules.requirement_extraction.models import (
    RequirementExtractionRecord,
    RequirementExtractionSet,
    RequirementSourceLink,
)
from src.shared.db.base import utcnow
from src.shared.enums import EventSeverity, RequirementExtractionStatus
from src.shared.errors import NotFoundError
from src.shared.ids import next_requirement_extraction_id, next_requirement_extraction_set_id


def _get_set(session: Session, requirement_extraction_set_id: str) -> RequirementExtractionSet:
    record = session.scalar(
        select(RequirementExtractionSet).where(
            RequirementExtractionSet.requirement_extraction_set_id == requirement_extraction_set_id
        )
    )
    if not record:
        raise NotFoundError(f"Requirement extraction set '{requirement_extraction_set_id}' was not found")
    return record


def _get_record(session: Session, requirement_extraction_id: str) -> RequirementExtractionRecord:
    record = session.scalar(
        select(RequirementExtractionRecord).where(
            RequirementExtractionRecord.requirement_extraction_id == requirement_extraction_id
        )
    )
    if not record:
        raise NotFoundError(f"Requirement extraction record '{requirement_extraction_id}' was not found")
    return record


def _get_records(session: Session, requirement_extraction_set_id: str) -> list[RequirementExtractionRecord]:
    return list(
        session.scalars(
            select(RequirementExtractionRecord)
            .where(RequirementExtractionRecord.requirement_extraction_set_id == requirement_extraction_set_id)
            .order_by(RequirementExtractionRecord.created_at.asc(), RequirementExtractionRecord.id.asc())
        )
    )


def _get_links(session: Session, requirement_extraction_id: str) -> list[RequirementSourceLink]:
    return list(
        session.scalars(
            select(RequirementSourceLink)
            .where(RequirementSourceLink.requirement_extraction_id == requirement_extraction_id)
            .order_by(RequirementSourceLink.created_at.asc(), RequirementSourceLink.id.asc())
        )
    )


def build_requirement_extraction(session: Session, document_set_id: str) -> RequirementExtractionSet:
    document_set, items, _runs = get_document_set(session, document_set_id)
    extraction_set = RequirementExtractionSet(
        requirement_extraction_set_id=next_requirement_extraction_set_id(
            session, RequirementExtractionSet.requirement_extraction_set_id
        ),
        document_set_id=document_set.document_set_id,
        extraction_status=RequirementExtractionStatus.BUILT,
    )
    session.add(extraction_set)
    session.flush()
    try:
        requirement_specs: list[tuple[str, str, str, str]] = []
        for idx, item in enumerate(items, start=1):
            requirement_specs.append(
                (
                    f"REQ-{idx:03d}",
                    f"Проверить и отразить требования из документа роли {item.item_role} ({item.source_file_name}).",
                    "DOCUMENT_ANALYSIS" if item.item_role in {"TZ", "TECH_SPEC"} else "NOTICE_ANALYSIS",
                    item.artifact_ref,
                )
            )
        if not requirement_specs:
            requirement_specs.append(
                ("REQ-001", "Набор документов пуст, требуется ручная классификация требований.", "UNKNOWN", document_set.document_set_id)
            )

        for requirement_code, requirement_text, requirement_group, source_ref in requirement_specs:
            record = RequirementExtractionRecord(
                requirement_extraction_id=next_requirement_extraction_id(
                    session, RequirementExtractionRecord.requirement_extraction_id
                ),
                requirement_extraction_set_id=extraction_set.requirement_extraction_set_id,
                requirement_code=requirement_code,
                requirement_text=requirement_text,
                requirement_group=requirement_group,
            )
            session.add(record)
            session.flush()
            session.add(RequirementSourceLink(requirement_extraction_id=record.requirement_extraction_id, source_ref=source_ref))

        append_event_record(
            session,
            deal_id=document_set.deal_id,
            event_code="requirement_extraction_built",
            source_module_id="M-012",
            severity=EventSeverity.INFO,
            payload_json={
                "requirement_extraction_set_id": extraction_set.requirement_extraction_set_id,
                "document_set_id": document_set.document_set_id,
                "requirement_count": len(requirement_specs),
            },
        )
        session.commit()
        session.refresh(extraction_set)
        return extraction_set
    except Exception as exc:
        extraction_set.extraction_status = RequirementExtractionStatus.FAILED
        extraction_set.updated_at = utcnow()
        append_event_record(
            session,
            deal_id=document_set.deal_id,
            event_code="requirement_extraction_failed",
            source_module_id="M-012",
            severity=EventSeverity.HIGH,
            payload_json={
                "requirement_extraction_set_id": extraction_set.requirement_extraction_set_id,
                "document_set_id": document_set.document_set_id,
                "error": str(exc),
            },
        )
        session.commit()
        raise


def get_requirement_extraction_set(
    session: Session,
    requirement_extraction_set_id: str,
) -> tuple[RequirementExtractionSet, list[tuple[RequirementExtractionRecord, list[RequirementSourceLink]]]]:
    extraction_set = _get_set(session, requirement_extraction_set_id)
    records = [(record, _get_links(session, record.requirement_extraction_id)) for record in _get_records(session, requirement_extraction_set_id)]
    return extraction_set, records


def get_requirement_extraction_record(
    session: Session,
    requirement_extraction_id: str,
) -> tuple[RequirementExtractionRecord, list[RequirementSourceLink]]:
    record = _get_record(session, requirement_extraction_id)
    return record, _get_links(session, requirement_extraction_id)


def list_requirement_extraction_sets(
    session: Session,
    *,
    document_set_id: str | None = None,
) -> list[tuple[RequirementExtractionSet, list[tuple[RequirementExtractionRecord, list[RequirementSourceLink]]]]]:
    query = select(RequirementExtractionSet).order_by(
        RequirementExtractionSet.created_at.desc(),
        RequirementExtractionSet.id.desc(),
    )
    if document_set_id:
        query = query.where(RequirementExtractionSet.document_set_id == document_set_id)
    sets = list(session.scalars(query))
    return [get_requirement_extraction_set(session, item.requirement_extraction_set_id) for item in sets]
