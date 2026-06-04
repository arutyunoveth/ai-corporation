from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.event_log.service import append_event_record
from src.modules.execution_plans.models import (
    ExecutionPlanAssumption,
    ExecutionPlanMilestone,
    ExecutionPlanRecord,
    ExecutionPlanSet,
)
from src.modules.execution_plans.schemas import BuildExecutionPlanRequest
from src.shared.db.base import utcnow
from src.shared.enums import EventSeverity, ExecutionPlanStatus, MilestoneState
from src.shared.errors import NotFoundError, ValidationError
from src.shared.execution_entry_package import load_execution_entry_context
from src.shared.ids import (
    next_execution_plan_id,
    next_execution_plan_milestone_id,
    next_execution_plan_set_id,
)

_DEFAULT_PLAN_MILESTONES = [
    ("EP-CONTRACT", "Supplier Contract Alignment", 0, MilestoneState.DONE),
    ("EP-PRODUCTION", "Production / Picking Start", 5, MilestoneState.PLANNED),
    ("EP-READINESS", "Supplier Readiness Confirmation", 12, MilestoneState.PLANNED),
    ("EP-DISPATCH", "Dispatch to Delivery", 18, MilestoneState.PLANNED),
]


def _get_set(session: Session, execution_plan_set_id: str) -> ExecutionPlanSet:
    record = session.scalar(
        select(ExecutionPlanSet).where(ExecutionPlanSet.execution_plan_set_id == execution_plan_set_id)
    )
    if not record:
        raise NotFoundError(f"Execution plan set '{execution_plan_set_id}' was not found")
    return record


def _get_record(session: Session, execution_plan_id: str) -> ExecutionPlanRecord:
    record = session.scalar(
        select(ExecutionPlanRecord).where(ExecutionPlanRecord.execution_plan_id == execution_plan_id)
    )
    if not record:
        raise NotFoundError(f"Execution plan record '{execution_plan_id}' was not found")
    return record


def _get_records(session: Session, execution_plan_set_id: str) -> list[ExecutionPlanRecord]:
    return list(
        session.scalars(
            select(ExecutionPlanRecord)
            .where(ExecutionPlanRecord.execution_plan_set_id == execution_plan_set_id)
            .order_by(ExecutionPlanRecord.created_at.asc(), ExecutionPlanRecord.id.asc())
        )
    )


def _get_milestones(session: Session, execution_plan_id: str) -> list[ExecutionPlanMilestone]:
    return list(
        session.scalars(
            select(ExecutionPlanMilestone)
            .where(ExecutionPlanMilestone.execution_plan_id == execution_plan_id)
            .order_by(ExecutionPlanMilestone.created_at.asc(), ExecutionPlanMilestone.id.asc())
        )
    )


def _get_assumptions(session: Session, execution_plan_id: str) -> list[ExecutionPlanAssumption]:
    return list(
        session.scalars(
            select(ExecutionPlanAssumption)
            .where(ExecutionPlanAssumption.execution_plan_id == execution_plan_id)
            .order_by(ExecutionPlanAssumption.created_at.asc(), ExecutionPlanAssumption.id.asc())
        )
    )


def build_execution_plan(session: Session, payload: BuildExecutionPlanRequest) -> ExecutionPlanSet:
    context = load_execution_entry_context(session, deal_id=payload.deal_id)
    if not context.supplier_contract_set or not context.supplier_contract_record:
        raise ValidationError("Execution plan requires a canonical supplier contract draft context")

    plan_set = ExecutionPlanSet(
        execution_plan_set_id=next_execution_plan_set_id(session, ExecutionPlanSet.execution_plan_set_id),
        deal_id=payload.deal_id,
        plan_status=ExecutionPlanStatus.BUILT,
    )
    session.add(plan_set)
    session.flush()
    try:
        manifest = {
            "supplier_contract_set_id": context.supplier_contract_set.supplier_contract_set_id,
            "supplier_contract_id": context.supplier_contract_record.supplier_contract_id,
            "supplier_id": context.supplier_contract_set.supplier_id,
            "delivery_milestone_helper_set_id": context.delivery_milestone_set.delivery_milestone_set_id
            if context.delivery_milestone_set
            else None,
            "helper_milestone_count": len(context.delivery_milestones),
        }
        summary_text = (
            f"Execution plan baseline prepared for supplier {context.supplier_contract_set.supplier_id}. "
            f"Helper milestones imported={len(context.delivery_milestones)}."
        )
        record = ExecutionPlanRecord(
            execution_plan_id=next_execution_plan_id(session, ExecutionPlanRecord.execution_plan_id),
            execution_plan_set_id=plan_set.execution_plan_set_id,
            summary_text=summary_text,
            baseline_manifest_json=manifest,
        )
        session.add(record)
        session.flush()

        if context.delivery_milestones:
            for helper_record, _helper_events in context.delivery_milestones:
                session.add(
                    ExecutionPlanMilestone(
                        execution_plan_milestone_id=next_execution_plan_milestone_id(
                            session, ExecutionPlanMilestone.execution_plan_milestone_id
                        ),
                        execution_plan_id=record.execution_plan_id,
                        milestone_code=helper_record.milestone_code,
                        milestone_name=helper_record.milestone_name,
                        due_date=helper_record.due_date,
                        milestone_state=helper_record.milestone_state,
                    )
                )
                session.flush()
        else:
            now = utcnow()
            for code, name, offset, state in _DEFAULT_PLAN_MILESTONES:
                session.add(
                    ExecutionPlanMilestone(
                        execution_plan_milestone_id=next_execution_plan_milestone_id(
                            session, ExecutionPlanMilestone.execution_plan_milestone_id
                        ),
                        execution_plan_id=record.execution_plan_id,
                        milestone_code=code,
                        milestone_name=name,
                        due_date=now + timedelta(days=offset),
                        milestone_state=state,
                    )
                )
                session.flush()

        assumptions = [
            ("SUPPLIER_ID", f"Execution baseline is tied to supplier {context.supplier_contract_set.supplier_id}."),
            ("CONTRACT_DRAFT", "Supplier contract draft must be converted into signed operational terms before launch."),
        ]
        if context.supplier_quote:
            assumptions.append(
                ("SUPPLIER_QUOTE", f"Planning uses supplier quote {context.supplier_quote.quote_id} as commercial proxy.")
            )
        if context.contract_negotiation_issues:
            assumptions.append(
                ("NEGOTIATION_REVIEW", "Execution launch depends on resolving open negotiation issues.")
            )
        for code, text in assumptions:
            session.add(
                ExecutionPlanAssumption(
                    execution_plan_id=record.execution_plan_id,
                    assumption_code=code,
                    assumption_text=text,
                )
            )

        plan_set.updated_at = utcnow()
        session.add(plan_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="execution_plan_built",
            source_module_id="M-036",
            severity=EventSeverity.INFO,
            payload_json={
                "execution_plan_set_id": plan_set.execution_plan_set_id,
                "execution_plan_id": record.execution_plan_id,
                "supplier_contract_set_id": context.supplier_contract_set.supplier_contract_set_id,
            },
        )
        session.commit()
    except Exception as exc:
        plan_set.plan_status = ExecutionPlanStatus.FAILED
        plan_set.updated_at = utcnow()
        session.add(plan_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="execution_plan_failed",
            source_module_id="M-036",
            severity=EventSeverity.HIGH,
            payload_json={"execution_plan_set_id": plan_set.execution_plan_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(plan_set)
    return plan_set


def get_execution_plan_set(
    session: Session,
    execution_plan_set_id: str,
) -> tuple[ExecutionPlanSet, list[tuple[ExecutionPlanRecord, list[ExecutionPlanMilestone], list[ExecutionPlanAssumption]]]]:
    plan_set = _get_set(session, execution_plan_set_id)
    records = _get_records(session, execution_plan_set_id)
    return plan_set, [
        (record, _get_milestones(session, record.execution_plan_id), _get_assumptions(session, record.execution_plan_id))
        for record in records
    ]


def list_execution_plan_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[ExecutionPlanSet, list[tuple[ExecutionPlanRecord, list[ExecutionPlanMilestone], list[ExecutionPlanAssumption]]]]]:
    query = select(ExecutionPlanSet).order_by(ExecutionPlanSet.created_at.desc(), ExecutionPlanSet.id.desc())
    if deal_id:
        query = query.where(ExecutionPlanSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_execution_plan_set(session, item.execution_plan_set_id) for item in sets]


def get_execution_plan_record(
    session: Session,
    execution_plan_id: str,
) -> tuple[ExecutionPlanRecord, list[ExecutionPlanMilestone], list[ExecutionPlanAssumption]]:
    record = _get_record(session, execution_plan_id)
    return record, _get_milestones(session, execution_plan_id), _get_assumptions(session, execution_plan_id)
