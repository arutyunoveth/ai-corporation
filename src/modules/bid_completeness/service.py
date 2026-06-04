from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.bid_completeness.models import (
    BidCompletenessFlag,
    BidCompletenessRecord,
    BidReadinessReport,
    BidCompletenessSet,
)
from src.modules.bid_completeness.schemas import CheckBidCompletenessRequest
from src.modules.bid_documents.service import get_bid_document_collection_set
from src.modules.bid_packages.service import get_bid_package_set
from src.modules.document_requirements.service import get_document_requirement_set
from src.modules.event_log.service import append_event_record
from src.shared.db.base import utcnow
from src.shared.enums import (
    BidCompletenessStatus,
    BidDocumentRowStatus,
    DocumentRequirementStatus,
    EventSeverity,
    RiskSeverity,
)
from src.shared.errors import NotFoundError
from src.shared.ids import next_bid_completeness_id, next_bid_completeness_set_id, next_bid_readiness_report_id
from src.shared.validation import require_same_reference


def _get_set(session: Session, bid_completeness_set_id: str) -> BidCompletenessSet:
    record = session.scalar(
        select(BidCompletenessSet).where(BidCompletenessSet.bid_completeness_set_id == bid_completeness_set_id)
    )
    if not record:
        raise NotFoundError(f"Bid completeness set '{bid_completeness_set_id}' was not found")
    return record


def _get_records(session: Session, bid_completeness_set_id: str) -> list[BidCompletenessRecord]:
    return list(
        session.scalars(
            select(BidCompletenessRecord)
            .where(BidCompletenessRecord.bid_completeness_set_id == bid_completeness_set_id)
            .order_by(BidCompletenessRecord.created_at.asc(), BidCompletenessRecord.id.asc())
        )
    )


def _get_flags(session: Session, bid_completeness_id: str) -> list[BidCompletenessFlag]:
    return list(
        session.scalars(
            select(BidCompletenessFlag)
            .where(BidCompletenessFlag.bid_completeness_id == bid_completeness_id)
            .order_by(BidCompletenessFlag.created_at.asc(), BidCompletenessFlag.id.asc())
        )
    )


def _get_reports(session: Session, bid_completeness_set_id: str) -> list[BidReadinessReport]:
    return list(
        session.scalars(
            select(BidReadinessReport)
            .where(BidReadinessReport.bid_completeness_set_id == bid_completeness_set_id)
            .order_by(BidReadinessReport.created_at.asc(), BidReadinessReport.id.asc())
        )
    )


def check_bid_completeness(session: Session, payload: CheckBidCompletenessRequest) -> BidCompletenessSet:
    package_set, package_records = get_bid_package_set(session, payload.bid_package_set_id)
    require_same_reference(payload.deal_id, package_set.deal_id, "deal_id")
    requirement_set_id = payload.document_requirement_set_id
    if requirement_set_id is None:
        collection_set, _collection_rows, _bindings = get_bid_document_collection_set(
            session, package_set.bid_document_collection_set_id
        )
        requirement_set_id = collection_set.document_requirement_set_id
    requirement_set, requirement_rows = get_document_requirement_set(session, requirement_set_id)
    require_same_reference(payload.deal_id, requirement_set.deal_id, "deal_id")
    collection_set, collection_rows, _bindings = get_bid_document_collection_set(session, package_set.bid_document_collection_set_id)

    package_record, package_items = package_records[0]
    package_artifact_refs = {item.artifact_ref for item in package_items}
    collection_map = {row.requirement_row_ref: row for row in collection_rows}

    completeness_set = BidCompletenessSet(
        bid_completeness_set_id=next_bid_completeness_set_id(session, BidCompletenessSet.bid_completeness_set_id),
        deal_id=payload.deal_id,
        bid_package_set_id=package_set.bid_package_set_id,
        completeness_status=BidCompletenessStatus.COMPLETE,
    )
    session.add(completeness_set)
    session.flush()
    append_event_record(
        session,
        deal_id=payload.deal_id,
        event_code="bid_completeness_check_started",
        source_module_id="M-031",
        severity=EventSeverity.INFO,
        payload_json={"bid_completeness_set_id": completeness_set.bid_completeness_set_id},
    )
    try:
        flags_data: list[dict] = []
        mandatory_total = 0
        mandatory_present = 0
        optional_present = 0

        for row in requirement_rows:
            collection_row = collection_map.get(row.row_code)
            is_present = bool(row.source_artifact_ref and row.source_artifact_ref in package_artifact_refs)
            status = str(row.requirement_status)

            if status == str(DocumentRequirementStatus.REQUIRED):
                mandatory_total += 1
                if is_present:
                    mandatory_present += 1
                else:
                    flags_data.append(
                        {
                            "flag_code": "MISSING_REQUIRED_BID_DOC",
                            "severity": RiskSeverity.HIGH,
                            "summary": f"Required bid document '{row.requirement_title}' is not present in the package.",
                            "source_ref": f"{requirement_set.document_requirement_set_id}:{row.row_code}",
                        }
                    )
            elif status in {str(DocumentRequirementStatus.OPTIONAL), str(DocumentRequirementStatus.CONDITIONAL)} and is_present:
                optional_present += 1

            if collection_row and str(collection_row.collection_status) == str(BidDocumentRowStatus.PENDING):
                flags_data.append(
                    {
                        "flag_code": "PENDING_COLLECTION_ITEM",
                        "severity": RiskSeverity.MEDIUM,
                        "summary": f"Bid collection item for '{row.requirement_title}' is still pending.",
                        "source_ref": f"{collection_set.bid_document_collection_set_id}:{row.row_code}",
                    }
                )
            if row.requires_manual_review or status == str(DocumentRequirementStatus.UNKNOWN):
                flags_data.append(
                    {
                        "flag_code": "MANUAL_REVIEW_REQUIRED",
                        "severity": RiskSeverity.MEDIUM,
                        "summary": f"Requirement '{row.requirement_title}' still requires manual review.",
                        "source_ref": f"{requirement_set.document_requirement_set_id}:{row.row_code}",
                    }
                )

        if mandatory_present < mandatory_total:
            completeness_status = BidCompletenessStatus.INCOMPLETE
        elif any(flag["severity"] == RiskSeverity.MEDIUM for flag in flags_data):
            completeness_status = BidCompletenessStatus.NEEDS_REVIEW
        else:
            completeness_status = BidCompletenessStatus.COMPLETE

        summary_text = (
            f"Mandatory present: {mandatory_present}/{mandatory_total}. "
            f"Optional present: {optional_present}. "
            f"Completeness status: {completeness_status}."
        )

        record = BidCompletenessRecord(
            bid_completeness_id=next_bid_completeness_id(session, BidCompletenessRecord.bid_completeness_id),
            bid_completeness_set_id=completeness_set.bid_completeness_set_id,
            mandatory_total=mandatory_total,
            mandatory_present=mandatory_present,
            optional_present=optional_present,
            summary_text=summary_text,
        )
        session.add(record)
        session.flush()
        for flag_data in flags_data:
            session.add(BidCompletenessFlag(bid_completeness_id=record.bid_completeness_id, **flag_data))
        blocking_issue_count = sum(1 for flag_data in flags_data if flag_data["severity"] in {RiskSeverity.HIGH, RiskSeverity.CRITICAL})
        readiness_summary = (
            f"Readiness contour for package {package_set.bid_package_set_id}: "
            f"status={completeness_status}, blocking_issues={blocking_issue_count}, "
            f"mandatory_present={mandatory_present}/{mandatory_total}."
        )
        report = BidReadinessReport(
            bid_readiness_report_id=next_bid_readiness_report_id(
                session, BidReadinessReport.bid_readiness_report_id
            ),
            bid_completeness_set_id=completeness_set.bid_completeness_set_id,
            readiness_summary=readiness_summary,
            blocking_issue_count=blocking_issue_count,
        )
        session.add(report)
        completeness_set.completeness_status = completeness_status
        completeness_set.updated_at = utcnow()
        session.add(completeness_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="bid_completeness_checked",
            source_module_id="M-031",
            severity=EventSeverity.INFO,
            payload_json={
                "bid_completeness_set_id": completeness_set.bid_completeness_set_id,
                "bid_completeness_id": record.bid_completeness_id,
                "completeness_status": str(completeness_status),
            },
        )
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="bid_readiness_report_built",
            source_module_id="M-031",
            severity=EventSeverity.INFO,
            payload_json={
                "bid_completeness_set_id": completeness_set.bid_completeness_set_id,
                "bid_readiness_report_id": report.bid_readiness_report_id,
                "blocking_issue_count": blocking_issue_count,
            },
        )
        session.commit()
    except Exception as exc:
        completeness_set.completeness_status = BidCompletenessStatus.INCOMPLETE
        completeness_set.updated_at = utcnow()
        session.add(completeness_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="bid_completeness_failed",
            source_module_id="M-031",
            severity=EventSeverity.HIGH,
            payload_json={"bid_completeness_set_id": completeness_set.bid_completeness_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(completeness_set)
    return completeness_set


def get_bid_completeness_set(
    session: Session,
    bid_completeness_set_id: str,
) -> tuple[BidCompletenessSet, list[tuple[BidCompletenessRecord, list[BidCompletenessFlag]]], list[BidReadinessReport]]:
    completeness_set = _get_set(session, bid_completeness_set_id)
    records = _get_records(session, bid_completeness_set_id)
    return (
        completeness_set,
        [(record, _get_flags(session, record.bid_completeness_id)) for record in records],
        _get_reports(session, bid_completeness_set_id),
    )


def list_bid_completeness_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[BidCompletenessSet, list[tuple[BidCompletenessRecord, list[BidCompletenessFlag]]]]]:
    query = select(BidCompletenessSet).order_by(BidCompletenessSet.created_at.desc())
    if deal_id:
        query = query.where(BidCompletenessSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_bid_completeness_set(session, item.bid_completeness_set_id) for item in sets]


def get_bid_completeness_record(
    session: Session,
    bid_completeness_id: str,
) -> tuple[BidCompletenessRecord, list[BidCompletenessFlag]]:
    record = session.scalar(
        select(BidCompletenessRecord).where(BidCompletenessRecord.bid_completeness_id == bid_completeness_id)
    )
    if not record:
        raise NotFoundError(f"Bid completeness record '{bid_completeness_id}' was not found")
    return record, _get_flags(session, bid_completeness_id)
