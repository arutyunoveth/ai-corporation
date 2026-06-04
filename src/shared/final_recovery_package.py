from dataclasses import dataclass

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from src.modules.acceptance_control.models import AcceptanceControlRecord, AcceptanceControlSet
from src.modules.archive_export.models import ArchiveExportRecord, ArchiveExportSet
from src.modules.claim_triggers.models import ClaimTriggerRecord, ClaimTriggerSet
from src.modules.closing_docs.models import ClosingDocsRecord, ClosingDocsSet
from src.modules.dashboard_snapshots.models import DashboardSnapshotRecord, DashboardSnapshotSet
from src.modules.deal_closure.models import DealClosureRecord, DealClosureSet
from src.modules.incident_register.models import IncidentRegisterRecord, IncidentRegisterSet
from src.modules.kpi_learning.models import KPILearningRecord, KPILearningSet
from src.modules.payment_tracking.models import PaymentTrackingRecord, PaymentTrackingSet
from src.modules.supplier_contracts.models import SupplierContractRecord, SupplierContractSet
from src.shared.enums import DashboardScopeType


def _latest_by_deal(model: type, deal_id: str) -> Select:
    return select(model).where(model.deal_id == deal_id).order_by(model.created_at.desc(), model.id.desc())  # type: ignore[attr-defined]


def _latest_child(model: type, field: str, value: str) -> Select:
    return select(model).where(getattr(model, field) == value).order_by(model.created_at.desc(), model.id.desc())


@dataclass(slots=True)
class FinalRecoveryContext:
    deal_closure_set: DealClosureSet | None
    deal_closure_record: DealClosureRecord | None
    acceptance_control_set: AcceptanceControlSet | None
    acceptance_control_record: AcceptanceControlRecord | None
    closing_docs_set: ClosingDocsSet | None
    closing_docs_record: ClosingDocsRecord | None
    payment_tracking_set: PaymentTrackingSet | None
    payment_tracking_record: PaymentTrackingRecord | None
    claim_trigger_set: ClaimTriggerSet | None
    claim_trigger_record: ClaimTriggerRecord | None
    incident_register_set: IncidentRegisterSet | None
    incident_register_record: IncidentRegisterRecord | None
    kpi_learning_set: KPILearningSet | None
    kpi_learning_record: KPILearningRecord | None
    supplier_contract_set: SupplierContractSet | None
    supplier_contract_record: SupplierContractRecord | None
    archive_export_set: ArchiveExportSet | None
    archive_export_record: ArchiveExportRecord | None
    dashboard_snapshot_set: DashboardSnapshotSet | None
    dashboard_snapshot_record: DashboardSnapshotRecord | None


def load_final_recovery_context(session: Session, deal_id: str) -> FinalRecoveryContext:
    deal_closure_set = session.scalar(_latest_by_deal(DealClosureSet, deal_id))
    deal_closure_record = None
    if deal_closure_set:
        deal_closure_record = session.scalar(
            _latest_child(DealClosureRecord, "deal_closure_set_id", deal_closure_set.deal_closure_set_id)
        )

    acceptance_control_set = session.scalar(_latest_by_deal(AcceptanceControlSet, deal_id))
    acceptance_control_record = None
    if acceptance_control_set:
        acceptance_control_record = session.scalar(
            _latest_child(
                AcceptanceControlRecord,
                "acceptance_control_set_id",
                acceptance_control_set.acceptance_control_set_id,
            )
        )

    closing_docs_set = session.scalar(_latest_by_deal(ClosingDocsSet, deal_id))
    closing_docs_record = None
    if closing_docs_set:
        closing_docs_record = session.scalar(
            _latest_child(ClosingDocsRecord, "closing_docs_set_id", closing_docs_set.closing_docs_set_id)
        )

    payment_tracking_set = session.scalar(_latest_by_deal(PaymentTrackingSet, deal_id))
    payment_tracking_record = None
    if payment_tracking_set:
        payment_tracking_record = session.scalar(
            _latest_child(PaymentTrackingRecord, "payment_tracking_set_id", payment_tracking_set.payment_tracking_set_id)
        )

    claim_trigger_set = session.scalar(_latest_by_deal(ClaimTriggerSet, deal_id))
    claim_trigger_record = None
    if claim_trigger_set:
        claim_trigger_record = session.scalar(
            _latest_child(ClaimTriggerRecord, "claim_trigger_set_id", claim_trigger_set.claim_trigger_set_id)
        )

    incident_register_set = session.scalar(_latest_by_deal(IncidentRegisterSet, deal_id))
    incident_register_record = None
    if incident_register_set:
        incident_register_record = session.scalar(
            _latest_child(
                IncidentRegisterRecord,
                "incident_register_set_id",
                incident_register_set.incident_register_set_id,
            )
        )

    kpi_learning_set = session.scalar(_latest_by_deal(KPILearningSet, deal_id))
    kpi_learning_record = None
    if kpi_learning_set:
        kpi_learning_record = session.scalar(
            _latest_child(KPILearningRecord, "kpi_learning_set_id", kpi_learning_set.kpi_learning_set_id)
        )

    supplier_contract_set = session.scalar(_latest_by_deal(SupplierContractSet, deal_id))
    supplier_contract_record = None
    if supplier_contract_set:
        supplier_contract_record = session.scalar(
            _latest_child(
                SupplierContractRecord,
                "supplier_contract_set_id",
                supplier_contract_set.supplier_contract_set_id,
            )
        )

    archive_export_set = session.scalar(_latest_by_deal(ArchiveExportSet, deal_id))
    archive_export_record = None
    if archive_export_set:
        archive_export_record = session.scalar(
            _latest_child(ArchiveExportRecord, "archive_export_set_id", archive_export_set.archive_export_set_id)
        )

    dashboard_snapshot_set = session.scalar(
        select(DashboardSnapshotSet)
        .where(
            DashboardSnapshotSet.scope_type == DashboardScopeType.DEAL,
            DashboardSnapshotSet.scope_ref == deal_id,
        )
        .order_by(DashboardSnapshotSet.created_at.desc(), DashboardSnapshotSet.id.desc())
    )
    dashboard_snapshot_record = None
    if dashboard_snapshot_set:
        dashboard_snapshot_record = session.scalar(
            _latest_child(
                DashboardSnapshotRecord,
                "dashboard_snapshot_set_id",
                dashboard_snapshot_set.dashboard_snapshot_set_id,
            )
        )

    return FinalRecoveryContext(
        deal_closure_set=deal_closure_set,
        deal_closure_record=deal_closure_record,
        acceptance_control_set=acceptance_control_set,
        acceptance_control_record=acceptance_control_record,
        closing_docs_set=closing_docs_set,
        closing_docs_record=closing_docs_record,
        payment_tracking_set=payment_tracking_set,
        payment_tracking_record=payment_tracking_record,
        claim_trigger_set=claim_trigger_set,
        claim_trigger_record=claim_trigger_record,
        incident_register_set=incident_register_set,
        incident_register_record=incident_register_record,
        kpi_learning_set=kpi_learning_set,
        kpi_learning_record=kpi_learning_record,
        supplier_contract_set=supplier_contract_set,
        supplier_contract_record=supplier_contract_record,
        archive_export_set=archive_export_set,
        archive_export_record=archive_export_record,
        dashboard_snapshot_set=dashboard_snapshot_set,
        dashboard_snapshot_record=dashboard_snapshot_record,
    )
