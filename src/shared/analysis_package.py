from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.modules.deal_registry.models import Deal
from src.modules.deal_registry.service import get_deal
from src.modules.document_ingestion.models import DocumentIngestionRun, DocumentSet, DocumentSetItem
from src.modules.document_ingestion.service import get_document_set
from src.modules.tender_intake.models import TenderIntakeRecord, TenderSourcePayload
from src.modules.tender_intake.service import get_tender_intake
from src.modules.tender_summary.models import TenderSummary, TenderSummarySourceLink
from src.modules.tender_summary.service import get_tender_summary
from src.shared.validation import require_same_reference


@dataclass
class IntakePackage:
    deal: Deal
    intake: TenderIntakeRecord
    source_payload: TenderSourcePayload
    document_set: DocumentSet
    document_set_items: list[DocumentSetItem]
    document_set_runs: list[DocumentIngestionRun]
    tender_summary: TenderSummary
    tender_summary_source_links: list[TenderSummarySourceLink]


def load_intake_package(
    session: Session,
    *,
    deal_id: str,
    intake_id: str,
    document_set_id: str,
    tender_summary_id: str,
) -> IntakePackage:
    deal = get_deal(session, deal_id)
    intake, source_payload = get_tender_intake(session, intake_id)
    document_set, document_set_items, document_set_runs = get_document_set(session, document_set_id)
    tender_summary, tender_summary_source_links = get_tender_summary(session, tender_summary_id)

    require_same_reference(deal.deal_id, intake.deal_id, "deal_id")
    require_same_reference(deal.deal_id, document_set.deal_id, "deal_id")
    require_same_reference(deal.deal_id, tender_summary.deal_id, "deal_id")
    require_same_reference(intake.intake_id, document_set.intake_id, "intake_id")
    require_same_reference(intake.intake_id, tender_summary.intake_id, "intake_id")
    require_same_reference(document_set.document_set_id, tender_summary.document_set_id, "document_set_id")

    return IntakePackage(
        deal=deal,
        intake=intake,
        source_payload=source_payload,
        document_set=document_set,
        document_set_items=document_set_items,
        document_set_runs=document_set_runs,
        tender_summary=tender_summary,
        tender_summary_source_links=tender_summary_source_links,
    )
