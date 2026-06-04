from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.modules.acceptance_control.models import AcceptanceControlRecord, AcceptanceControlSet, AcceptanceRemark
from src.modules.action_queue.models import ActionQueueRecord, ActionQueueSet
from src.modules.claim_triggers.models import ClaimTriggerFlag, ClaimTriggerRecord, ClaimTriggerSet
from src.modules.contract_risks.models import ContractRiskFlag, ContractRiskRecord, ContractRiskSet
from src.modules.deal_registry.models import Deal
from src.modules.event_log.service import append_event_record
from src.modules.incident_register.models import IncidentRegisterFlag, IncidentRegisterRecord, IncidentRegisterSet
from src.modules.initial_tech_risks.models import InitialTechRiskFlag, InitialTechRiskFlagSet
from src.modules.launch_visibility.models import LaunchVisibilityItem, LaunchVisibilityRecord, LaunchVisibilitySet
from src.modules.payment_tracking.models import PaymentTrackingAlert, PaymentTrackingRecord, PaymentTrackingSet
from src.modules.procedure_monitor.models import ProcedureMonitorAlert, ProcedureMonitorRecord, ProcedureMonitorSet
from src.modules.supplier_progress.models import SupplierProgressAlert, SupplierProgressRecord, SupplierProgressSet
from src.modules.tender_screening.models import TenderScreeningRecord
from src.modules.workspace_feed.models import WorkspaceFeedItem, WorkspaceFeedRecord, WorkspaceFeedSet
from src.shared.db.base import utcnow
from src.shared.enums import (
    AcceptanceResolutionState,
    AcceptanceStatus,
    ClaimTriggerStatus,
    EventSeverity,
    IncidentRegisterStatus,
    LaunchVisibilityItemType,
    LaunchVisibilityScopeType,
    LaunchVisibilityStatus,
    PaymentTrackingStatus,
    ProcedureStatus,
    ScreeningResultStatus,
    SupplierReadinessState,
)
from src.shared.errors import NotFoundError
from src.shared.ids import next_launch_visibility_id, next_launch_visibility_set_id
from src.shared.validation import require_non_empty


def _get_set(session: Session, launch_visibility_set_id: str) -> LaunchVisibilitySet:
    record = session.scalar(
        select(LaunchVisibilitySet).where(LaunchVisibilitySet.launch_visibility_set_id == launch_visibility_set_id)
    )
    if not record:
        raise NotFoundError(f"Launch visibility set '{launch_visibility_set_id}' was not found")
    return record


def _get_record(session: Session, launch_visibility_id: str) -> LaunchVisibilityRecord:
    record = session.scalar(
        select(LaunchVisibilityRecord).where(LaunchVisibilityRecord.launch_visibility_id == launch_visibility_id)
    )
    if not record:
        raise NotFoundError(f"Launch visibility record '{launch_visibility_id}' was not found")
    return record


def _get_records(session: Session, launch_visibility_set_id: str) -> list[LaunchVisibilityRecord]:
    return list(
        session.scalars(
            select(LaunchVisibilityRecord)
            .where(LaunchVisibilityRecord.launch_visibility_set_id == launch_visibility_set_id)
            .order_by(LaunchVisibilityRecord.created_at.asc(), LaunchVisibilityRecord.id.asc())
        )
    )


def _get_items(session: Session, launch_visibility_id: str) -> list[LaunchVisibilityItem]:
    return list(
        session.scalars(
            select(LaunchVisibilityItem)
            .where(LaunchVisibilityItem.launch_visibility_id == launch_visibility_id)
            .order_by(LaunchVisibilityItem.created_at.asc(), LaunchVisibilityItem.id.asc())
        )
    )


def _normalize_severity(value: str | None) -> EventSeverity:
    normalized = (value or "").upper()
    if normalized in {EventSeverity.CRITICAL, "CRITICAL", "ESCALATED", "FAIL", "FAILED", "BLOCKED"}:
        return EventSeverity.CRITICAL
    if normalized in {EventSeverity.HIGH, "HIGH", "OVERDUE", "REJECTED"}:
        return EventSeverity.HIGH
    if normalized in {EventSeverity.WARNING, "WARNING", "MEDIUM", "PARTIAL", "NEEDS_REVIEW", "OPEN", "PENDING"}:
        return EventSeverity.WARNING
    return EventSeverity.INFO


def _item(
    *,
    deal_id: str | None,
    item_code: str,
    item_type: LaunchVisibilityItemType,
    severity: EventSeverity,
    source_module_id: str | None,
    source_ref: str | None,
    title: str,
    detail_text: str,
    requires_manual_review: bool = False,
) -> dict:
    return {
        "deal_id": deal_id,
        "item_code": item_code,
        "item_type": item_type,
        "severity": severity,
        "source_module_id": source_module_id,
        "source_ref": source_ref,
        "title": title,
        "detail_text": detail_text,
        "requires_manual_review": requires_manual_review,
    }


def _latest_set(session: Session, model, *conditions):
    return session.scalar(select(model).where(*conditions).order_by(model.created_at.desc(), model.id.desc()).limit(1))


def _latest_record_for_set(session: Session, model, set_field, set_id: str):
    return session.scalar(
        select(model).where(set_field == set_id).order_by(model.created_at.desc(), model.id.desc()).limit(1)
    )


def _severity_rank(severity: EventSeverity) -> int:
    if severity == EventSeverity.CRITICAL:
        return 4
    if severity == EventSeverity.HIGH:
        return 3
    if severity == EventSeverity.WARNING:
        return 2
    return 1


def _contains_blocker(items: Iterable[dict]) -> bool:
    for item in items:
        if item["item_type"] == LaunchVisibilityItemType.RED_FLAG:
            return True
        if _severity_rank(item["severity"]) >= _severity_rank(EventSeverity.HIGH):
            return True
    return False


def _collect_deal_items(session: Session, deal_id: str) -> list[dict]:
    deal = session.scalar(select(Deal).where(Deal.deal_id == deal_id))
    if not deal:
        raise NotFoundError(f"Deal '{deal_id}' was not found")

    items: list[dict] = [
        _item(
            deal_id=deal_id,
            item_code="DEAL_STATUS_OVERVIEW",
            item_type=LaunchVisibilityItemType.OVERVIEW,
            severity=EventSeverity.INFO,
            source_module_id="M-001",
            source_ref=deal.deal_id,
            title=f"Deal {deal.deal_id}",
            detail_text=f"Current deal status: {deal.current_status}.",
        )
    ]

    screening = session.scalar(
        select(TenderScreeningRecord)
        .where(TenderScreeningRecord.deal_id == deal_id)
        .order_by(TenderScreeningRecord.created_at.desc(), TenderScreeningRecord.id.desc())
        .limit(1)
    )
    if screening and screening.result_status in {ScreeningResultStatus.FAIL, ScreeningResultStatus.NEEDS_REVIEW}:
        items.append(
            _item(
                deal_id=deal_id,
                item_code="SCREENING_REVIEW",
                item_type=(
                    LaunchVisibilityItemType.RED_FLAG
                    if screening.result_status == ScreeningResultStatus.FAIL
                    else LaunchVisibilityItemType.ATTENTION
                ),
                severity=(
                    EventSeverity.HIGH if screening.result_status == ScreeningResultStatus.FAIL else EventSeverity.WARNING
                ),
                source_module_id="M-009",
                source_ref=screening.screening_id,
                title="Screening outcome requires review",
                detail_text=screening.rationale_text,
                requires_manual_review=screening.result_status == ScreeningResultStatus.NEEDS_REVIEW,
            )
        )

    tech_risk_set = _latest_set(session, InitialTechRiskFlagSet, InitialTechRiskFlagSet.deal_id == deal_id)
    if tech_risk_set:
        tech_flags = list(
            session.scalars(
                select(InitialTechRiskFlag)
                .where(InitialTechRiskFlag.risk_flag_set_id == tech_risk_set.risk_flag_set_id)
                .order_by(InitialTechRiskFlag.created_at.asc(), InitialTechRiskFlag.id.asc())
            )
        )
        for flag in tech_flags:
            severity = _normalize_severity(flag.severity)
            if _severity_rank(severity) < _severity_rank(EventSeverity.HIGH) and not flag.requires_manual_review:
                continue
            items.append(
                _item(
                    deal_id=deal_id,
                    item_code=f"TECH_{flag.row_code}",
                    item_type=(
                        LaunchVisibilityItemType.RED_FLAG
                        if severity in {EventSeverity.CRITICAL, EventSeverity.HIGH}
                        else LaunchVisibilityItemType.ATTENTION
                    ),
                    severity=severity,
                    source_module_id="M-015",
                    source_ref=flag.source_ref or flag.row_code,
                    title=f"Tech risk: {flag.risk_code}",
                    detail_text=flag.summary,
                    requires_manual_review=flag.requires_manual_review,
                )
            )

    contract_risk_set = _latest_set(session, ContractRiskSet, ContractRiskSet.deal_id == deal_id)
    if contract_risk_set:
        contract_records = list(
            session.scalars(
                select(ContractRiskRecord)
                .where(ContractRiskRecord.contract_risk_set_id == contract_risk_set.contract_risk_set_id)
                .order_by(ContractRiskRecord.created_at.asc(), ContractRiskRecord.id.asc())
            )
        )
        for record in contract_records:
            flags = list(
                session.scalars(
                    select(ContractRiskFlag)
                    .where(ContractRiskFlag.contract_risk_id == record.contract_risk_id)
                    .order_by(ContractRiskFlag.created_at.asc(), ContractRiskFlag.id.asc())
                )
            )
            for flag in flags:
                severity = _normalize_severity(flag.severity)
                if _severity_rank(severity) < _severity_rank(EventSeverity.HIGH):
                    continue
                items.append(
                    _item(
                        deal_id=deal_id,
                        item_code=flag.flag_code,
                        item_type=LaunchVisibilityItemType.RED_FLAG,
                        severity=severity,
                        source_module_id="M-026",
                        source_ref=flag.source_ref or record.contract_risk_id,
                        title=f"Contract risk: {record.clause_type}",
                        detail_text=flag.summary,
                    )
                )

    procedure_set = _latest_set(session, ProcedureMonitorSet, ProcedureMonitorSet.deal_id == deal_id)
    if procedure_set:
        procedure_record = _latest_record_for_set(
            session,
            ProcedureMonitorRecord,
            ProcedureMonitorRecord.procedure_monitor_set_id,
            procedure_set.procedure_monitor_set_id,
        )
        if procedure_set.procedure_status in {ProcedureStatus.WON_PENDING_CONTRACT, ProcedureStatus.BID_IN_PROGRESS}:
            items.append(
                _item(
                    deal_id=deal_id,
                    item_code="PROCEDURE_STATUS",
                    item_type=LaunchVisibilityItemType.HOTSPOT,
                    severity=EventSeverity.WARNING,
                    source_module_id="M-033",
                    source_ref=procedure_record.procedure_monitor_id if procedure_record else procedure_set.procedure_monitor_set_id,
                    title="Procedure monitoring requires active follow-up",
                    detail_text=(
                        procedure_record.summary_text
                        if procedure_record
                        else f"Procedure status is {procedure_set.procedure_status}."
                    ),
                )
            )
        if procedure_record:
            alerts = list(
                session.scalars(
                    select(ProcedureMonitorAlert)
                    .where(ProcedureMonitorAlert.procedure_monitor_id == procedure_record.procedure_monitor_id)
                    .order_by(ProcedureMonitorAlert.created_at.asc(), ProcedureMonitorAlert.id.asc())
                )
            )
            for alert in alerts:
                severity = _normalize_severity(alert.severity)
                if _severity_rank(severity) < _severity_rank(EventSeverity.WARNING):
                    continue
                items.append(
                    _item(
                        deal_id=deal_id,
                        item_code=alert.alert_code,
                        item_type=LaunchVisibilityItemType.ATTENTION,
                        severity=severity,
                        source_module_id="M-033",
                        source_ref=procedure_record.procedure_monitor_id,
                        title="Procedure alert",
                        detail_text=alert.summary,
                        requires_manual_review=True,
                    )
                )

    incident_set = _latest_set(session, IncidentRegisterSet, IncidentRegisterSet.deal_id == deal_id)
    if incident_set:
        incident_record = _latest_record_for_set(
            session,
            IncidentRegisterRecord,
            IncidentRegisterRecord.incident_register_set_id,
            incident_set.incident_register_set_id,
        )
        if incident_set.incident_status in {IncidentRegisterStatus.OPEN, IncidentRegisterStatus.ESCALATED} and incident_record:
            items.append(
                _item(
                    deal_id=deal_id,
                    item_code="INCIDENT_STATUS",
                    item_type=LaunchVisibilityItemType.RED_FLAG,
                    severity=_normalize_severity(incident_record.severity),
                    source_module_id="M-040",
                    source_ref=incident_record.incident_register_id,
                    title="Active incident in delivery contour",
                    detail_text=incident_record.summary_text,
                    requires_manual_review=True,
                )
            )
        if incident_record:
            flags = list(
                session.scalars(
                    select(IncidentRegisterFlag)
                    .where(IncidentRegisterFlag.incident_register_id == incident_record.incident_register_id)
                    .order_by(IncidentRegisterFlag.created_at.asc(), IncidentRegisterFlag.id.asc())
                )
            )
            for flag in flags:
                severity = _normalize_severity(flag.severity)
                if _severity_rank(severity) < _severity_rank(EventSeverity.WARNING):
                    continue
                items.append(
                    _item(
                        deal_id=deal_id,
                        item_code=flag.flag_code,
                        item_type=LaunchVisibilityItemType.RED_FLAG,
                        severity=severity,
                        source_module_id="M-040",
                        source_ref=incident_record.incident_register_id,
                        title="Incident register flag",
                        detail_text=flag.summary,
                        requires_manual_review=True,
                    )
                )

    payment_set = _latest_set(session, PaymentTrackingSet, PaymentTrackingSet.deal_id == deal_id)
    if payment_set:
        payment_record = _latest_record_for_set(
            session,
            PaymentTrackingRecord,
            PaymentTrackingRecord.payment_tracking_set_id,
            payment_set.payment_tracking_set_id,
        )
        if payment_record and (payment_set.payment_status == PaymentTrackingStatus.OVERDUE or payment_record.overdue_days > 0):
            items.append(
                _item(
                    deal_id=deal_id,
                    item_code="PAYMENT_OVERDUE",
                    item_type=LaunchVisibilityItemType.RED_FLAG,
                    severity=EventSeverity.HIGH,
                    source_module_id="M-043",
                    source_ref=payment_record.payment_tracking_id,
                    title="Payment overdue requires operator follow-up",
                    detail_text=payment_record.summary_text,
                    requires_manual_review=True,
                )
            )
        if payment_record:
            alerts = list(
                session.scalars(
                    select(PaymentTrackingAlert)
                    .where(PaymentTrackingAlert.payment_tracking_id == payment_record.payment_tracking_id)
                    .order_by(PaymentTrackingAlert.created_at.asc(), PaymentTrackingAlert.id.asc())
                )
            )
            for alert in alerts:
                severity = _normalize_severity(alert.severity)
                if _severity_rank(severity) < _severity_rank(EventSeverity.WARNING):
                    continue
                items.append(
                    _item(
                        deal_id=deal_id,
                        item_code=alert.alert_code,
                        item_type=LaunchVisibilityItemType.ATTENTION,
                        severity=severity,
                        source_module_id="M-043",
                        source_ref=payment_record.payment_tracking_id,
                        title="Payment tracking alert",
                        detail_text=alert.summary,
                        requires_manual_review=True,
                    )
                )

    claim_set = _latest_set(session, ClaimTriggerSet, ClaimTriggerSet.deal_id == deal_id)
    if claim_set:
        claim_record = _latest_record_for_set(
            session,
            ClaimTriggerRecord,
            ClaimTriggerRecord.claim_trigger_set_id,
            claim_set.claim_trigger_set_id,
        )
        if claim_record and claim_set.trigger_status in {ClaimTriggerStatus.TRIGGERED, ClaimTriggerStatus.ESCALATED}:
            items.append(
                _item(
                    deal_id=deal_id,
                    item_code="CLAIM_TRIGGER_ACTIVE",
                    item_type=LaunchVisibilityItemType.RED_FLAG,
                    severity=EventSeverity.CRITICAL if claim_set.trigger_status == ClaimTriggerStatus.ESCALATED else EventSeverity.HIGH,
                    source_module_id="M-044",
                    source_ref=claim_record.claim_trigger_id,
                    title="Claim path is active",
                    detail_text=claim_record.summary_text,
                    requires_manual_review=True,
                )
            )
        if claim_record:
            flags = list(
                session.scalars(
                    select(ClaimTriggerFlag)
                    .where(ClaimTriggerFlag.claim_trigger_id == claim_record.claim_trigger_id)
                    .order_by(ClaimTriggerFlag.created_at.asc(), ClaimTriggerFlag.id.asc())
                )
            )
            for flag in flags:
                severity = _normalize_severity(flag.severity)
                if _severity_rank(severity) < _severity_rank(EventSeverity.WARNING):
                    continue
                items.append(
                    _item(
                        deal_id=deal_id,
                        item_code=flag.flag_code,
                        item_type=LaunchVisibilityItemType.RED_FLAG,
                        severity=severity,
                        source_module_id="M-044",
                        source_ref=claim_record.claim_trigger_id,
                        title="Claim trigger flag",
                        detail_text=flag.summary,
                        requires_manual_review=True,
                    )
                )

    progress_set = _latest_set(session, SupplierProgressSet, SupplierProgressSet.deal_id == deal_id)
    if progress_set:
        progress_record = _latest_record_for_set(
            session,
            SupplierProgressRecord,
            SupplierProgressRecord.supplier_progress_set_id,
            progress_set.supplier_progress_set_id,
        )
        if progress_record and progress_record.readiness_state in {SupplierReadinessState.DELAYED, SupplierReadinessState.BLOCKED}:
            items.append(
                _item(
                    deal_id=deal_id,
                    item_code="SUPPLIER_PROGRESS",
                    item_type=LaunchVisibilityItemType.ATTENTION,
                    severity=EventSeverity.WARNING,
                    source_module_id="M-038",
                    source_ref=progress_record.supplier_progress_id,
                    title="Supplier progress needs attention",
                    detail_text=progress_record.summary_text,
                    requires_manual_review=True,
                )
            )
        if progress_record:
            alerts = list(
                session.scalars(
                    select(SupplierProgressAlert)
                    .where(SupplierProgressAlert.supplier_progress_id == progress_record.supplier_progress_id)
                    .order_by(SupplierProgressAlert.created_at.asc(), SupplierProgressAlert.id.asc())
                )
            )
            for alert in alerts:
                severity = _normalize_severity(alert.severity)
                if _severity_rank(severity) < _severity_rank(EventSeverity.WARNING):
                    continue
                items.append(
                    _item(
                        deal_id=deal_id,
                        item_code=alert.alert_code,
                        item_type=LaunchVisibilityItemType.ATTENTION,
                        severity=severity,
                        source_module_id="M-038",
                        source_ref=progress_record.supplier_progress_id,
                        title="Supplier progress alert",
                        detail_text=alert.summary,
                    )
                )

    acceptance_set = _latest_set(session, AcceptanceControlSet, AcceptanceControlSet.deal_id == deal_id)
    if acceptance_set:
        acceptance_record = _latest_record_for_set(
            session,
            AcceptanceControlRecord,
            AcceptanceControlRecord.acceptance_control_set_id,
            acceptance_set.acceptance_control_set_id,
        )
        if acceptance_record and (
            acceptance_set.acceptance_status in {AcceptanceStatus.PARTIAL, AcceptanceStatus.NEEDS_REVIEW, AcceptanceStatus.REJECTED}
            or acceptance_record.resolution_state != AcceptanceResolutionState.RESOLVED
        ):
            items.append(
                _item(
                    deal_id=deal_id,
                    item_code="ACCEPTANCE_REVIEW",
                    item_type=LaunchVisibilityItemType.ATTENTION,
                    severity=(
                        EventSeverity.HIGH if acceptance_set.acceptance_status == AcceptanceStatus.REJECTED else EventSeverity.WARNING
                    ),
                    source_module_id="M-041",
                    source_ref=acceptance_record.acceptance_control_id,
                    title="Acceptance contour still needs review",
                    detail_text=acceptance_record.summary_text,
                    requires_manual_review=True,
                )
            )
        if acceptance_record:
            remarks = list(
                session.scalars(
                    select(AcceptanceRemark)
                    .where(AcceptanceRemark.acceptance_control_id == acceptance_record.acceptance_control_id)
                    .order_by(AcceptanceRemark.created_at.asc(), AcceptanceRemark.id.asc())
                )
            )
            for remark in remarks:
                severity = _normalize_severity(remark.severity)
                if _severity_rank(severity) < _severity_rank(EventSeverity.WARNING):
                    continue
                items.append(
                    _item(
                        deal_id=deal_id,
                        item_code=remark.remark_code,
                        item_type=LaunchVisibilityItemType.ATTENTION,
                        severity=severity,
                        source_module_id="M-041",
                        source_ref=acceptance_record.acceptance_control_id,
                        title="Acceptance remark",
                        detail_text=remark.remark_text,
                        requires_manual_review=True,
                    )
                )

    workspace_set = _latest_set(
        session,
        WorkspaceFeedSet,
        WorkspaceFeedSet.scope_type == "DEAL",
        WorkspaceFeedSet.scope_ref == deal_id,
    )
    if workspace_set:
        workspace_record = _latest_record_for_set(
            session,
            WorkspaceFeedRecord,
            WorkspaceFeedRecord.workspace_feed_set_id,
            workspace_set.workspace_feed_set_id,
        )
        if workspace_record:
            workspace_items = list(
                session.scalars(
                    select(WorkspaceFeedItem)
                    .where(WorkspaceFeedItem.workspace_feed_id == workspace_record.workspace_feed_id)
                    .order_by(WorkspaceFeedItem.created_at.asc(), WorkspaceFeedItem.id.asc())
                )
            )
            for workspace_item in workspace_items[:3]:
                severity = _normalize_severity(workspace_item.priority)
                if _severity_rank(severity) < _severity_rank(EventSeverity.WARNING):
                    continue
                items.append(
                    _item(
                        deal_id=deal_id,
                        item_code=workspace_item.item_code,
                        item_type=LaunchVisibilityItemType.HOTSPOT,
                        severity=severity,
                        source_module_id="WORKSPACE-FEED",
                        source_ref=workspace_item.source_ref or workspace_record.workspace_feed_id,
                        title="Workspace hotspot",
                        detail_text=workspace_item.item_text,
                    )
                )

    action_queue_set = _latest_set(
        session,
        ActionQueueSet,
        ActionQueueSet.scope_type == "DEAL",
        ActionQueueSet.scope_ref == deal_id,
    )
    if action_queue_set:
        action_records = list(
            session.scalars(
                select(ActionQueueRecord)
                .where(ActionQueueRecord.action_queue_set_id == action_queue_set.action_queue_set_id)
                .order_by(ActionQueueRecord.created_at.asc(), ActionQueueRecord.id.asc())
            )
        )
        for action_record in action_records[:3]:
            if action_record.action_status not in {"PENDING", "APPROVED"}:
                continue
            items.append(
                _item(
                    deal_id=deal_id,
                    item_code=action_record.action_code,
                    item_type=LaunchVisibilityItemType.HOTSPOT,
                    severity=EventSeverity.WARNING,
                    source_module_id="ACTION-QUEUE",
                    source_ref=action_record.action_queue_id,
                    title="Action queue hotspot",
                    detail_text=action_record.action_text,
                )
            )

    return items


def _record_counts(items: list[dict], active_deal_count: int) -> dict:
    red_flag_count = sum(1 for item in items if item["item_type"] == LaunchVisibilityItemType.RED_FLAG)
    attention_count = sum(
        1
        for item in items
        if item["item_type"] in {LaunchVisibilityItemType.ATTENTION, LaunchVisibilityItemType.HOTSPOT}
    )
    manual_review_count = sum(1 for item in items if item["requires_manual_review"])
    overdue_count = sum(1 for item in items if "OVERDUE" in item["item_code"] or "PAYMENT" in item["item_code"])
    return {
        "active_deal_count": active_deal_count,
        "red_flag_count": red_flag_count,
        "attention_count": attention_count,
        "manual_review_count": manual_review_count,
        "overdue_count": overdue_count,
    }


def _build_deal_scope(session: Session, deal_id: str) -> tuple[str, list[dict], dict]:
    items = _collect_deal_items(session, deal_id)
    counts = _record_counts(items, active_deal_count=1)
    counts["blocked_deal_count"] = 1 if _contains_blocker(items) else 0
    summary = (
        f"Launch visibility for {deal_id}: red_flags={counts['red_flag_count']}, "
        f"attention={counts['attention_count']}, overdue={counts['overdue_count']}."
    )
    return summary, items, counts


def _build_pilot_scope(session: Session) -> tuple[str, list[dict], dict]:
    deal_ids = list(
        session.scalars(
            select(Deal.deal_id).order_by(Deal.created_at.asc(), Deal.id.asc())
        )
    )
    aggregated_items: list[dict] = []
    blocked_deals = 0
    for deal_id in deal_ids:
        deal_items = _collect_deal_items(session, deal_id)
        if _contains_blocker(deal_items):
            blocked_deals += 1
        aggregated_items.extend(deal_items)
    counts = _record_counts(aggregated_items, active_deal_count=len(deal_ids))
    counts["blocked_deal_count"] = blocked_deals
    summary = (
        f"Pilot visibility: deals={counts['active_deal_count']}, blocked={counts['blocked_deal_count']}, "
        f"red_flags={counts['red_flag_count']}, attention={counts['attention_count']}."
    )
    return summary, aggregated_items, counts


def build_launch_visibility(session: Session, scope_type: LaunchVisibilityScopeType, scope_ref: str) -> LaunchVisibilitySet:
    scope_ref = require_non_empty(scope_ref, "scope_ref")
    if scope_type == LaunchVisibilityScopeType.DEAL:
        deal = session.scalar(select(Deal).where(Deal.deal_id == scope_ref))
        if not deal:
            raise NotFoundError(f"Deal '{scope_ref}' was not found")

    visibility_set = LaunchVisibilitySet(
        launch_visibility_set_id=next_launch_visibility_set_id(
            session,
            LaunchVisibilitySet.launch_visibility_set_id,
        ),
        scope_type=scope_type,
        scope_ref=scope_ref,
        visibility_status=LaunchVisibilityStatus.BUILT,
    )
    session.add(visibility_set)
    session.flush()
    deal_id = scope_ref if scope_type == LaunchVisibilityScopeType.DEAL else None

    try:
        if scope_type == LaunchVisibilityScopeType.DEAL:
            summary, items, counts = _build_deal_scope(session, scope_ref)
        else:
            summary, items, counts = _build_pilot_scope(session)

        record = LaunchVisibilityRecord(
            launch_visibility_id=next_launch_visibility_id(session, LaunchVisibilityRecord.launch_visibility_id),
            launch_visibility_set_id=visibility_set.launch_visibility_set_id,
            summary_text=summary,
            active_deal_count=counts["active_deal_count"],
            blocked_deal_count=counts["blocked_deal_count"],
            attention_count=counts["attention_count"],
            red_flag_count=counts["red_flag_count"],
            manual_review_count=counts["manual_review_count"],
            overdue_count=counts["overdue_count"],
        )
        session.add(record)
        session.flush()

        if not items:
            items = [
                _item(
                    deal_id=deal_id,
                    item_code="PILOT_MONITOR_ONLY",
                    item_type=LaunchVisibilityItemType.OVERVIEW,
                    severity=EventSeverity.INFO,
                    source_module_id="L1-SUPPORT",
                    source_ref=visibility_set.launch_visibility_set_id,
                    title="No critical launch-support items detected",
                    detail_text="Only baseline monitoring is required for the current scope.",
                )
            ]

        for item in items:
            visibility_item = LaunchVisibilityItem(launch_visibility_id=record.launch_visibility_id, **item)
            session.add(visibility_item)
            session.flush()
            append_event_record(
                session,
                deal_id=visibility_item.deal_id or deal_id,
                event_code="launch_visibility_item_recorded",
                source_module_id="L1-SUPPORT",
                severity=visibility_item.severity,
                payload_json={
                    "launch_visibility_set_id": visibility_set.launch_visibility_set_id,
                    "launch_visibility_id": record.launch_visibility_id,
                    "item_code": visibility_item.item_code,
                    "item_type": visibility_item.item_type,
                    "source_module_id": visibility_item.source_module_id,
                    "scope_type": str(scope_type),
                },
            )

        visibility_set.updated_at = utcnow()
        append_event_record(
            session,
            deal_id=deal_id,
            event_code="launch_visibility_built",
            source_module_id="L1-SUPPORT",
            severity=EventSeverity.INFO,
            payload_json={
                "launch_visibility_set_id": visibility_set.launch_visibility_set_id,
                "launch_visibility_id": record.launch_visibility_id,
                "scope_type": str(scope_type),
                "scope_ref": scope_ref,
                "item_count": len(items),
                **counts,
            },
        )
        session.commit()
        session.refresh(visibility_set)
        return visibility_set
    except Exception as exc:
        visibility_set.visibility_status = LaunchVisibilityStatus.FAILED
        visibility_set.updated_at = utcnow()
        append_event_record(
            session,
            deal_id=deal_id,
            event_code="launch_visibility_failed",
            source_module_id="L1-SUPPORT",
            severity=EventSeverity.HIGH,
            payload_json={"scope_type": str(scope_type), "scope_ref": scope_ref, "error": str(exc)},
        )
        session.commit()
        raise


def get_launch_visibility_set(
    session: Session,
    launch_visibility_set_id: str,
) -> tuple[LaunchVisibilitySet, list[tuple[LaunchVisibilityRecord, list[LaunchVisibilityItem]]]]:
    visibility_set = _get_set(session, launch_visibility_set_id)
    records = [get_launch_visibility_record(session, item.launch_visibility_id) for item in _get_records(session, launch_visibility_set_id)]
    return visibility_set, records


def get_launch_visibility_record(
    session: Session,
    launch_visibility_id: str,
) -> tuple[LaunchVisibilityRecord, list[LaunchVisibilityItem]]:
    record = _get_record(session, launch_visibility_id)
    return record, _get_items(session, launch_visibility_id)


def list_launch_visibility_sets(
    session: Session,
    *,
    scope_type: LaunchVisibilityScopeType | None = None,
    scope_ref: str | None = None,
) -> list[tuple[LaunchVisibilitySet, list[tuple[LaunchVisibilityRecord, list[LaunchVisibilityItem]]]]]:
    query = select(LaunchVisibilitySet).order_by(LaunchVisibilitySet.created_at.desc(), LaunchVisibilitySet.id.desc())
    if scope_type:
        query = query.where(LaunchVisibilitySet.scope_type == scope_type)
    if scope_ref:
        query = query.where(LaunchVisibilitySet.scope_ref == scope_ref)
    return [get_launch_visibility_set(session, item.launch_visibility_set_id) for item in session.scalars(query)]
