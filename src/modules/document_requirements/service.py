from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.document_requirements.models import DocumentRequirementRow, DocumentRequirementSet
from src.modules.document_requirements.schemas import ExtractDocumentRequirementsRequest
from src.modules.event_log.service import append_event_record
from src.shared.analysis_package import load_intake_package
from src.shared.enums import DocumentRequirementStatus, EventSeverity
from src.shared.ids import next_document_requirement_set_id


def _derive_row(item, sequence_no: int) -> dict:
    if item.item_role == "NOTICE":
        status = DocumentRequirementStatus.REQUIRED
        title = "Извещение закупки"
        description = "Извещение должно быть доступно для downstream проверки сроков, условий и формальных требований."
        manual_review = False
    elif item.item_role == "TZ":
        status = DocumentRequirementStatus.REQUIRED
        title = "Техническое задание / спецификация"
        description = "Техническая спецификация должна быть доступна для анализа требований и построения compliance matrix."
        manual_review = False
    elif item.item_role == "DRAFT_CONTRACT":
        status = DocumentRequirementStatus.CONDITIONAL
        title = "Проект договора"
        description = "Проект договора нужен для дальнейшего contract/risk анализа, если он присутствует в документации."
        manual_review = False
    elif item.item_role == "ATTACHMENT":
        status = DocumentRequirementStatus.OPTIONAL
        title = f"Приложение: {item.source_file_name}"
        description = "Дополнительное приложение может понадобиться для детальной проверки контекста закупки."
        manual_review = False
    else:
        status = DocumentRequirementStatus.UNKNOWN
        title = f"Неидентифицированный документ: {item.source_file_name}"
        description = "Документ требует ручной классификации перед bid prep."
        manual_review = True
    return {
        "row_code": f"DR-{sequence_no:04d}",
        "sequence_no": sequence_no,
        "requirement_title": title,
        "requirement_description": description,
        "requirement_category": item.item_role,
        "requirement_status": status,
        "source_artifact_ref": item.artifact_ref,
        "source_pointer": f"DOCUMENT_SET:{item.document_set_id}:{item.source_file_name}",
        "notes": None,
        "requires_manual_review": manual_review,
    }


def extract_document_requirements(
    session: Session,
    payload: ExtractDocumentRequirementsRequest,
) -> tuple[DocumentRequirementSet, list[DocumentRequirementRow]]:
    package = load_intake_package(
        session,
        deal_id=payload.deal_id,
        intake_id=payload.intake_id,
        document_set_id=payload.document_set_id,
        tender_summary_id=payload.tender_summary_id,
    )
    append_event_record(
        session,
        deal_id=package.deal.deal_id,
        event_code="document_requirements_extraction_started",
        source_module_id="M-014",
        severity=EventSeverity.INFO,
        payload_json={"document_set_id": package.document_set.document_set_id},
    )
    try:
        rows_data = [_derive_row(item, index) for index, item in enumerate(package.document_set_items, start=1)]
        manual_review = any(row["requires_manual_review"] for row in rows_data)
        notes = "Some document roles require manual review." if manual_review else None
        requirement_set = DocumentRequirementSet(
            document_requirement_set_id=next_document_requirement_set_id(
                session,
                DocumentRequirementSet.document_requirement_set_id,
            ),
            deal_id=package.deal.deal_id,
            intake_id=package.intake.intake_id,
            document_set_id=package.document_set.document_set_id,
            tender_summary_id=package.tender_summary.tender_summary_id,
            requirement_count=len(rows_data),
            requires_manual_review=manual_review,
            notes=notes,
        )
        session.add(requirement_set)
        session.flush()
        rows: list[DocumentRequirementRow] = []
        for row_data in rows_data:
            row = DocumentRequirementRow(document_requirement_set_id=requirement_set.document_requirement_set_id, **row_data)
            session.add(row)
            rows.append(row)
        session.flush()
        append_event_record(
            session,
            deal_id=package.deal.deal_id,
            event_code="document_requirements_extracted",
            source_module_id="M-014",
            severity=EventSeverity.INFO,
            payload_json={
                "document_requirement_set_id": requirement_set.document_requirement_set_id,
                "requirement_count": requirement_set.requirement_count,
            },
        )
        session.commit()
        session.refresh(requirement_set)
        return requirement_set, rows
    except Exception as exc:
        append_event_record(
            session,
            deal_id=package.deal.deal_id,
            event_code="document_requirements_extraction_failed",
            source_module_id="M-014",
            severity=EventSeverity.HIGH,
            payload_json={"error": str(exc)},
        )
        session.commit()
        raise


def get_document_requirement_set(
    session: Session,
    document_requirement_set_id: str,
) -> tuple[DocumentRequirementSet, list[DocumentRequirementRow]]:
    from src.shared.errors import NotFoundError

    requirement_set = session.scalar(
        select(DocumentRequirementSet).where(
            DocumentRequirementSet.document_requirement_set_id == document_requirement_set_id
        )
    )
    if not requirement_set:
        raise NotFoundError(f"Document requirement set '{document_requirement_set_id}' was not found")
    rows = list(
        session.scalars(
            select(DocumentRequirementRow)
            .where(DocumentRequirementRow.document_requirement_set_id == document_requirement_set_id)
            .order_by(DocumentRequirementRow.sequence_no.asc(), DocumentRequirementRow.id.asc())
        )
    )
    return requirement_set, rows


def list_document_requirement_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[DocumentRequirementSet, list[DocumentRequirementRow]]]:
    query = select(DocumentRequirementSet).order_by(DocumentRequirementSet.created_at.desc())
    if deal_id:
        query = query.where(DocumentRequirementSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_document_requirement_set(session, item.document_requirement_set_id) for item in sets]

