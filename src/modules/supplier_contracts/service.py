from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.event_log.service import append_event_record
from src.modules.supplier_contracts.models import (
    SupplierContractComment,
    SupplierContractObligation,
    SupplierContractRecord,
    SupplierContractSet,
)
from src.modules.supplier_contracts.schemas import BuildSupplierContractRequest
from src.shared.db.base import utcnow
from src.shared.enums import (
    EventSeverity,
    SupplierContractObligationStatus,
    SupplierContractStatus,
)
from src.shared.errors import NotFoundError, ValidationError
from src.shared.execution_entry_package import load_execution_entry_context
from src.shared.ids import next_supplier_contract_id, next_supplier_contract_set_id


def _get_set(session: Session, supplier_contract_set_id: str) -> SupplierContractSet:
    record = session.scalar(
        select(SupplierContractSet).where(SupplierContractSet.supplier_contract_set_id == supplier_contract_set_id)
    )
    if not record:
        raise NotFoundError(f"Supplier contract set '{supplier_contract_set_id}' was not found")
    return record


def _get_record(session: Session, supplier_contract_id: str) -> SupplierContractRecord:
    record = session.scalar(
        select(SupplierContractRecord).where(SupplierContractRecord.supplier_contract_id == supplier_contract_id)
    )
    if not record:
        raise NotFoundError(f"Supplier contract record '{supplier_contract_id}' was not found")
    return record


def _get_records(session: Session, supplier_contract_set_id: str) -> list[SupplierContractRecord]:
    return list(
        session.scalars(
            select(SupplierContractRecord)
            .where(SupplierContractRecord.supplier_contract_set_id == supplier_contract_set_id)
            .order_by(SupplierContractRecord.created_at.asc(), SupplierContractRecord.id.asc())
        )
    )


def _get_obligations(session: Session, supplier_contract_id: str) -> list[SupplierContractObligation]:
    return list(
        session.scalars(
            select(SupplierContractObligation)
            .where(SupplierContractObligation.supplier_contract_id == supplier_contract_id)
            .order_by(SupplierContractObligation.created_at.asc(), SupplierContractObligation.id.asc())
        )
    )


def _get_comments(session: Session, supplier_contract_id: str) -> list[SupplierContractComment]:
    return list(
        session.scalars(
            select(SupplierContractComment)
            .where(SupplierContractComment.supplier_contract_id == supplier_contract_id)
            .order_by(SupplierContractComment.created_at.asc(), SupplierContractComment.id.asc())
        )
    )


def build_supplier_contract(session: Session, payload: BuildSupplierContractRequest) -> SupplierContractSet:
    context = load_execution_entry_context(session, deal_id=payload.deal_id, supplier_id=payload.supplier_id)
    if not context.supplier_profile:
        raise ValidationError(f"Supplier '{payload.supplier_id}' does not exist")
    if not context.contract_negotiation_set or not context.contract_negotiation_record:
        raise ValidationError("Supplier contract draft requires a canonical contract negotiation workspace")
    if context.quote_recommendation and context.quote_recommendation.recommended_supplier_id != payload.supplier_id:
        if not context.supplier_quote:
            raise ValidationError("Supplier contract can be built only for the selected or quoted supplier")

    contract_set = SupplierContractSet(
        supplier_contract_set_id=next_supplier_contract_set_id(
            session, SupplierContractSet.supplier_contract_set_id
        ),
        deal_id=payload.deal_id,
        supplier_id=payload.supplier_id,
        contract_status=SupplierContractStatus.DRAFT,
    )
    session.add(contract_set)
    session.flush()
    try:
        manifest = {
            "supplier_display_name": context.supplier_profile.display_name,
            "contract_negotiation_set_id": context.contract_negotiation_set.contract_negotiation_set_id,
            "contract_negotiation_id": context.contract_negotiation_record.contract_negotiation_id,
            "issue_count": len(context.contract_negotiation_issues),
            "comment_count": len(context.contract_negotiation_comments),
            "quote_comparison_set_id": context.quote_comparison_set.quote_comparison_set_id
            if context.quote_comparison_set
            else None,
            "recommended_supplier_id": context.quote_recommendation.recommended_supplier_id
            if context.quote_recommendation
            else None,
            "supplier_quote_id": context.supplier_quote.quote_id if context.supplier_quote else None,
        }
        summary_text = (
            f"Supplier back-to-back draft prepared for {context.supplier_profile.display_name}. "
            f"Negotiation issues={len(context.contract_negotiation_issues)}."
        )
        record = SupplierContractRecord(
            supplier_contract_id=next_supplier_contract_id(session, SupplierContractRecord.supplier_contract_id),
            supplier_contract_set_id=contract_set.supplier_contract_set_id,
            summary_text=summary_text,
            contract_manifest_json=manifest,
        )
        session.add(record)
        session.flush()

        if context.contract_negotiation_issues:
            for issue in context.contract_negotiation_issues:
                session.add(
                    SupplierContractObligation(
                        supplier_contract_id=record.supplier_contract_id,
                        obligation_code=issue.issue_code,
                        obligation_text=issue.issue_text,
                        obligation_status=SupplierContractObligationStatus.NEEDS_REVIEW,
                    )
                )
        else:
            session.add(
                SupplierContractObligation(
                    supplier_contract_id=record.supplier_contract_id,
                    obligation_code="SUPPLY_SCOPE",
                    obligation_text="Supplier must fulfill the agreed delivery scope under mirrored commercial terms.",
                    obligation_status=SupplierContractObligationStatus.PENDING,
                )
            )

        if context.contract_negotiation_comments:
            for comment in context.contract_negotiation_comments:
                session.add(
                    SupplierContractComment(
                        supplier_contract_id=record.supplier_contract_id,
                        clause_ref=comment.clause_ref,
                        comment_text=comment.comment_text,
                    )
                )
        else:
            session.add(
                SupplierContractComment(
                    supplier_contract_id=record.supplier_contract_id,
                    clause_ref="COMMERCIAL_TERMS",
                    comment_text="Draft opened from supplier selection context; commercial terms require confirmation.",
                )
            )

        contract_set.updated_at = utcnow()
        session.add(contract_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="supplier_contract_built",
            source_module_id="M-035",
            severity=EventSeverity.INFO,
            payload_json={
                "supplier_contract_set_id": contract_set.supplier_contract_set_id,
                "supplier_contract_id": record.supplier_contract_id,
                "supplier_id": payload.supplier_id,
            },
        )
        session.commit()
    except Exception as exc:
        contract_set.contract_status = SupplierContractStatus.FAILED
        contract_set.updated_at = utcnow()
        session.add(contract_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="supplier_contract_failed",
            source_module_id="M-035",
            severity=EventSeverity.HIGH,
            payload_json={"supplier_contract_set_id": contract_set.supplier_contract_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(contract_set)
    return contract_set


def get_supplier_contract_set(
    session: Session,
    supplier_contract_set_id: str,
) -> tuple[SupplierContractSet, list[tuple[SupplierContractRecord, list[SupplierContractObligation], list[SupplierContractComment]]]]:
    contract_set = _get_set(session, supplier_contract_set_id)
    records = _get_records(session, supplier_contract_set_id)
    return contract_set, [
        (record, _get_obligations(session, record.supplier_contract_id), _get_comments(session, record.supplier_contract_id))
        for record in records
    ]


def list_supplier_contract_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[SupplierContractSet, list[tuple[SupplierContractRecord, list[SupplierContractObligation], list[SupplierContractComment]]]]]:
    query = select(SupplierContractSet).order_by(SupplierContractSet.created_at.desc(), SupplierContractSet.id.desc())
    if deal_id:
        query = query.where(SupplierContractSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_supplier_contract_set(session, item.supplier_contract_set_id) for item in sets]


def get_supplier_contract_record(
    session: Session,
    supplier_contract_id: str,
) -> tuple[SupplierContractRecord, list[SupplierContractObligation], list[SupplierContractComment]]:
    record = _get_record(session, supplier_contract_id)
    return record, _get_obligations(session, supplier_contract_id), _get_comments(session, supplier_contract_id)
