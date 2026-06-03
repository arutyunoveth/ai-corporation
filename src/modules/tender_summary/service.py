from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.deal_registry.service import get_deal
from src.modules.document_ingestion.service import get_document_set
from src.modules.event_log.service import append_event_record
from src.modules.tender_intake.service import get_tender_intake
from src.modules.tender_summary.models import TenderSummary, TenderSummarySourceLink
from src.modules.tender_summary.schemas import BuildTenderSummaryRequest
from src.shared.db.base import utcnow
from src.shared.enums import EventSeverity, TenderSummaryStatus
from src.shared.ids import next_tender_summary_id
from src.shared.validation import require_same_reference


def _scope_label(domain_type: str) -> str:
    mapping = {
        "ELECTRICAL_EQUIPMENT": "Поставка электротехнического оборудования",
    }
    return mapping.get(domain_type, domain_type.replace("_", " ").title())


def _get_tender_summary(session: Session, tender_summary_id: str) -> TenderSummary:
    summary = session.scalar(select(TenderSummary).where(TenderSummary.tender_summary_id == tender_summary_id))
    if not summary:
        from src.shared.errors import NotFoundError

        raise NotFoundError(f"Tender summary '{tender_summary_id}' was not found")
    return summary


def _get_source_links(session: Session, tender_summary_id: str) -> list[TenderSummarySourceLink]:
    return list(
        session.scalars(
            select(TenderSummarySourceLink)
            .where(TenderSummarySourceLink.tender_summary_id == tender_summary_id)
            .order_by(TenderSummarySourceLink.created_at.asc(), TenderSummarySourceLink.id.asc())
        )
    )


def build_tender_summary(session: Session, payload: BuildTenderSummaryRequest) -> TenderSummary:
    deal = get_deal(session, payload.deal_id)
    intake, _ = get_tender_intake(session, payload.intake_id)
    document_set, items, _ = get_document_set(session, payload.document_set_id)
    require_same_reference(deal.deal_id, intake.deal_id, "deal_id")
    require_same_reference(deal.deal_id, document_set.deal_id, "deal_id")
    require_same_reference(intake.intake_id, document_set.intake_id, "intake_id")

    append_event_record(
        session,
        deal_id=deal.deal_id,
        event_code="tender_summary_build_started",
        source_module_id="M-012",
        severity=EventSeverity.INFO,
        payload_json={
            "intake_id": intake.intake_id,
            "document_set_id": document_set.document_set_id,
        },
    )
    try:
        structured_summary = {
            "title": intake.source_title or deal.title,
            "customer_name": intake.source_customer_name or deal.customer_name,
            "procurement_number": intake.source_procurement_number or deal.procurement_number,
            "source_type": intake.source_type,
            "document_count": document_set.item_count,
            "high_level_scope": _scope_label(deal.domain_type),
            "summary_version": "1.0",
        }
        roles = ", ".join(item.item_role for item in items) if items else "нет зарегистрированных ролей"
        summary_text = (
            f"{structured_summary['title']}. "
            f"Заказчик: {structured_summary['customer_name']}. "
            f"Номер закупки: {structured_summary.get('procurement_number') or 'не указан'}. "
            f"Источник intake: {structured_summary['source_type']}. "
            f"Документов в наборе: {structured_summary['document_count']}. "
            f"Высокоуровневый scope: {structured_summary.get('high_level_scope') or 'не указан'}. "
            f"Роли документов: {roles}."
        )

        summary = TenderSummary(
            tender_summary_id=next_tender_summary_id(session, TenderSummary.tender_summary_id),
            deal_id=deal.deal_id,
            intake_id=intake.intake_id,
            document_set_id=document_set.document_set_id,
            summary_status=TenderSummaryStatus.BUILT,
            summary_text=summary_text,
            structured_summary_json=structured_summary,
        )
        session.add(summary)
        session.flush()

        source_links = [
            ("DEAL", deal.deal_id),
            ("INTAKE", intake.intake_id),
            ("DOCUMENT_SET", document_set.document_set_id),
        ] + [("ARTIFACT", item.artifact_ref) for item in items]
        for source_object_type, source_object_ref in source_links:
            session.add(
                TenderSummarySourceLink(
                    tender_summary_id=summary.tender_summary_id,
                    source_object_type=source_object_type,
                    source_object_ref=source_object_ref,
                )
            )

        append_event_record(
            session,
            deal_id=deal.deal_id,
            event_code="tender_summary_built",
            source_module_id="M-012",
            severity=EventSeverity.INFO,
            payload_json={
                "tender_summary_id": summary.tender_summary_id,
                "document_set_id": document_set.document_set_id,
            },
        )
        session.commit()
    except Exception as exc:
        append_event_record(
            session,
            deal_id=deal.deal_id,
            event_code="tender_summary_failed",
            source_module_id="M-012",
            severity=EventSeverity.HIGH,
            payload_json={
                "intake_id": intake.intake_id,
                "document_set_id": document_set.document_set_id,
                "error": str(exc),
            },
        )
        session.commit()
        raise

    session.refresh(summary)
    return summary


def get_tender_summary(session: Session, tender_summary_id: str) -> tuple[TenderSummary, list[TenderSummarySourceLink]]:
    summary = _get_tender_summary(session, tender_summary_id)
    return summary, _get_source_links(session, tender_summary_id)


def list_tender_summaries(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[TenderSummary, list[TenderSummarySourceLink]]]:
    query = select(TenderSummary).order_by(TenderSummary.created_at.desc())
    if deal_id:
        query = query.where(TenderSummary.deal_id == deal_id)
    summaries = list(session.scalars(query))
    return [(summary, _get_source_links(session, summary.tender_summary_id)) for summary in summaries]

