from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.bid_documents.service import get_bid_document_collection_set
from src.modules.bid_packages.models import BidPackageItem, BidPackageRecord, BidPackageSet
from src.modules.bid_packages.schemas import BuildBidPackageRequest
from src.modules.document_requirements.service import get_document_requirement_set
from src.modules.event_log.service import append_event_record
from src.shared.db.base import utcnow
from src.shared.enums import BidDocumentRowStatus, BidPackageItemRole, BidPackageStatus, EventSeverity
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import next_bid_package_id, next_bid_package_set_id
from src.shared.validation import require_same_reference


def _get_set(session: Session, bid_package_set_id: str) -> BidPackageSet:
    record = session.scalar(select(BidPackageSet).where(BidPackageSet.bid_package_set_id == bid_package_set_id))
    if not record:
        raise NotFoundError(f"Bid package set '{bid_package_set_id}' was not found")
    return record


def _get_records(session: Session, bid_package_set_id: str) -> list[BidPackageRecord]:
    return list(
        session.scalars(
            select(BidPackageRecord)
            .where(BidPackageRecord.bid_package_set_id == bid_package_set_id)
            .order_by(BidPackageRecord.package_version_no.asc(), BidPackageRecord.id.asc())
        )
    )


def _get_items(session: Session, bid_package_id: str) -> list[BidPackageItem]:
    return list(
        session.scalars(
            select(BidPackageItem)
            .where(BidPackageItem.bid_package_id == bid_package_id)
            .order_by(BidPackageItem.sort_order.asc(), BidPackageItem.id.asc())
        )
    )


def _item_role_for_requirement(row) -> str:
    category = str(row.requirement_category)
    if category in {"NOTICE", "TZ"}:
        return BidPackageItemRole.PRIMARY_DOC
    if category == "ATTACHMENT":
        return BidPackageItemRole.ATTACHMENT
    if category == "DRAFT_CONTRACT":
        return BidPackageItemRole.ATTACHMENT
    return BidPackageItemRole.OTHER


def build_bid_package(session: Session, payload: BuildBidPackageRequest) -> BidPackageSet:
    collection_set, collection_rows, _bindings = get_bid_document_collection_set(session, payload.bid_document_collection_set_id)
    require_same_reference(payload.deal_id, collection_set.deal_id, "deal_id")
    requirement_set, requirement_rows = get_document_requirement_set(session, collection_set.document_requirement_set_id)
    requirement_map = {row.row_code: row for row in requirement_rows}

    collected_rows = [row for row in collection_rows if str(row.collection_status) == str(BidDocumentRowStatus.COLLECTED) and row.artifact_ref]
    if not collected_rows:
        raise ValidationError("Bid package requires at least one collected artifact in the formal collection set")

    package_set = BidPackageSet(
        bid_package_set_id=next_bid_package_set_id(session, BidPackageSet.bid_package_set_id),
        deal_id=payload.deal_id,
        bid_document_collection_set_id=collection_set.bid_document_collection_set_id,
        package_status=BidPackageStatus.BUILT,
    )
    session.add(package_set)
    session.flush()
    append_event_record(
        session,
        deal_id=payload.deal_id,
        event_code="bid_package_build_started",
        source_module_id="M-030",
        severity=EventSeverity.INFO,
        payload_json={"bid_package_set_id": package_set.bid_package_set_id},
    )
    try:
        manifest_json = {
            "package_version_no": 1,
            "source_collection_status": str(collection_set.collection_status),
            "requirement_set_id": requirement_set.document_requirement_set_id,
            "item_count": len(collected_rows),
            "artifact_refs": [row.artifact_ref for row in collected_rows if row.artifact_ref],
        }
        package_record = BidPackageRecord(
            bid_package_id=next_bid_package_id(session, BidPackageRecord.bid_package_id),
            bid_package_set_id=package_set.bid_package_set_id,
            package_version_no=1,
            manifest_json=manifest_json,
        )
        session.add(package_record)
        session.flush()
        for index, row in enumerate(collected_rows, start=1):
            requirement_row = requirement_map.get(row.requirement_row_ref)
            item_role = _item_role_for_requirement(requirement_row) if requirement_row else BidPackageItemRole.OTHER
            session.add(
                BidPackageItem(
                    bid_package_id=package_record.bid_package_id,
                    artifact_ref=row.artifact_ref,
                    item_role=item_role,
                    sort_order=index,
                )
            )
        package_set.updated_at = utcnow()
        session.add(package_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="bid_package_built",
            source_module_id="M-030",
            severity=EventSeverity.INFO,
            payload_json={
                "bid_package_set_id": package_set.bid_package_set_id,
                "bid_package_id": package_record.bid_package_id,
                "item_count": len(collected_rows),
            },
        )
        session.commit()
    except Exception as exc:
        package_set.package_status = BidPackageStatus.FAILED
        package_set.updated_at = utcnow()
        session.add(package_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="bid_package_failed",
            source_module_id="M-030",
            severity=EventSeverity.HIGH,
            payload_json={"bid_package_set_id": package_set.bid_package_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(package_set)
    return package_set


def get_bid_package_set(
    session: Session,
    bid_package_set_id: str,
) -> tuple[BidPackageSet, list[tuple[BidPackageRecord, list[BidPackageItem]]]]:
    package_set = _get_set(session, bid_package_set_id)
    records = _get_records(session, bid_package_set_id)
    return package_set, [(record, _get_items(session, record.bid_package_id)) for record in records]


def list_bid_package_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[BidPackageSet, list[tuple[BidPackageRecord, list[BidPackageItem]]]]]:
    query = select(BidPackageSet).order_by(BidPackageSet.created_at.desc())
    if deal_id:
        query = query.where(BidPackageSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_bid_package_set(session, item.bid_package_set_id) for item in sets]


def get_bid_package_record(
    session: Session,
    bid_package_id: str,
) -> tuple[BidPackageRecord, list[BidPackageItem]]:
    record = session.scalar(select(BidPackageRecord).where(BidPackageRecord.bid_package_id == bid_package_id))
    if not record:
        raise NotFoundError(f"Bid package record '{bid_package_id}' was not found")
    return record, _get_items(session, bid_package_id)
