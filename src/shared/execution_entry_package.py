from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.contract_negotiation.models import (
    ContractNegotiationComment,
    ContractNegotiationIssue,
    ContractNegotiationRecord,
    ContractNegotiationSet,
)
from src.modules.delivery_milestones.models import (
    DeliveryMilestoneEvent,
    DeliveryMilestoneRecord,
    DeliveryMilestoneSet,
)
from src.modules.execution_plans.models import (
    ExecutionPlanAssumption,
    ExecutionPlanMilestone,
    ExecutionPlanRecord,
    ExecutionPlanSet,
)
from src.modules.purchase_orders.models import (
    PurchaseOrderItem,
    PurchaseOrderLink,
    PurchaseOrderRecord,
    PurchaseOrderSet,
)
from src.modules.quote_comparison.models import (
    QuoteComparisonRecommendation,
    QuoteComparisonSet,
)
from src.modules.quote_repository.models import QuoteRecord
from src.modules.supplier_contracts.models import (
    SupplierContractComment,
    SupplierContractObligation,
    SupplierContractRecord,
    SupplierContractSet,
)
from src.modules.supplier_fulfillment.models import (
    SupplierFulfillmentEvent,
    SupplierFulfillmentRecord,
    SupplierFulfillmentSet,
)
from src.modules.supplier_registry.models import SupplierProfile


@dataclass(slots=True)
class ExecutionEntryContext:
    deal_id: str
    supplier_id: str | None = None
    quote_comparison_set: QuoteComparisonSet | None = None
    quote_recommendation: QuoteComparisonRecommendation | None = None
    recommended_quote: QuoteRecord | None = None
    supplier_quote: QuoteRecord | None = None
    supplier_profile: SupplierProfile | None = None
    contract_negotiation_set: ContractNegotiationSet | None = None
    contract_negotiation_record: ContractNegotiationRecord | None = None
    contract_negotiation_issues: list[ContractNegotiationIssue] = field(default_factory=list)
    contract_negotiation_comments: list[ContractNegotiationComment] = field(default_factory=list)
    supplier_contract_set: SupplierContractSet | None = None
    supplier_contract_record: SupplierContractRecord | None = None
    supplier_contract_obligations: list[SupplierContractObligation] = field(default_factory=list)
    supplier_contract_comments: list[SupplierContractComment] = field(default_factory=list)
    execution_plan_set: ExecutionPlanSet | None = None
    execution_plan_record: ExecutionPlanRecord | None = None
    execution_plan_milestones: list[ExecutionPlanMilestone] = field(default_factory=list)
    execution_plan_assumptions: list[ExecutionPlanAssumption] = field(default_factory=list)
    purchase_order_set: PurchaseOrderSet | None = None
    purchase_order_record: PurchaseOrderRecord | None = None
    purchase_order_items: list[PurchaseOrderItem] = field(default_factory=list)
    purchase_order_links: list[PurchaseOrderLink] = field(default_factory=list)
    delivery_milestone_set: DeliveryMilestoneSet | None = None
    delivery_milestones: list[tuple[DeliveryMilestoneRecord, list[DeliveryMilestoneEvent]]] = field(default_factory=list)
    supplier_fulfillment_set: SupplierFulfillmentSet | None = None
    supplier_fulfillment_record: SupplierFulfillmentRecord | None = None
    supplier_fulfillment_events: list[SupplierFulfillmentEvent] = field(default_factory=list)


def load_execution_entry_context(
    session: Session,
    *,
    deal_id: str,
    supplier_id: str | None = None,
) -> ExecutionEntryContext:
    context = ExecutionEntryContext(deal_id=deal_id, supplier_id=supplier_id)

    comparison_set = session.scalar(
        select(QuoteComparisonSet)
        .where(QuoteComparisonSet.deal_id == deal_id)
        .order_by(QuoteComparisonSet.created_at.desc(), QuoteComparisonSet.id.desc())
        .limit(1)
    )
    if comparison_set:
        context.quote_comparison_set = comparison_set
        context.quote_recommendation = session.scalar(
            select(QuoteComparisonRecommendation).where(
                QuoteComparisonRecommendation.quote_comparison_set_id == comparison_set.quote_comparison_set_id
            )
        )
        if context.quote_recommendation:
            context.recommended_quote = session.scalar(
                select(QuoteRecord).where(QuoteRecord.quote_id == context.quote_recommendation.recommended_quote_id)
            )

    if supplier_id:
        context.supplier_profile = session.scalar(
            select(SupplierProfile).where(SupplierProfile.supplier_id == supplier_id)
        )
        context.supplier_quote = session.scalar(
            select(QuoteRecord)
            .where(
                QuoteRecord.supplier_id == supplier_id,
                QuoteRecord.quote_set_id == comparison_set.quote_set_id if comparison_set else True,
            )
            .order_by(QuoteRecord.created_at.desc(), QuoteRecord.id.desc())
            .limit(1)
        )

    negotiation_set = session.scalar(
        select(ContractNegotiationSet)
        .where(ContractNegotiationSet.deal_id == deal_id)
        .order_by(ContractNegotiationSet.created_at.desc(), ContractNegotiationSet.id.desc())
        .limit(1)
    )
    if negotiation_set:
        context.contract_negotiation_set = negotiation_set
        context.contract_negotiation_record = session.scalar(
            select(ContractNegotiationRecord)
            .where(ContractNegotiationRecord.contract_negotiation_set_id == negotiation_set.contract_negotiation_set_id)
            .order_by(ContractNegotiationRecord.created_at.desc(), ContractNegotiationRecord.id.desc())
            .limit(1)
        )
        if context.contract_negotiation_record:
            context.contract_negotiation_issues = list(
                session.scalars(
                    select(ContractNegotiationIssue)
                    .where(
                        ContractNegotiationIssue.contract_negotiation_id
                        == context.contract_negotiation_record.contract_negotiation_id
                    )
                    .order_by(ContractNegotiationIssue.created_at.asc(), ContractNegotiationIssue.id.asc())
                )
            )
            context.contract_negotiation_comments = list(
                session.scalars(
                    select(ContractNegotiationComment)
                    .where(
                        ContractNegotiationComment.contract_negotiation_id
                        == context.contract_negotiation_record.contract_negotiation_id
                    )
                    .order_by(ContractNegotiationComment.created_at.asc(), ContractNegotiationComment.id.asc())
                )
            )

    supplier_contract_query = select(SupplierContractSet).where(SupplierContractSet.deal_id == deal_id)
    if supplier_id:
        supplier_contract_query = supplier_contract_query.where(SupplierContractSet.supplier_id == supplier_id)
    supplier_contract_set = session.scalar(
        supplier_contract_query.order_by(SupplierContractSet.created_at.desc(), SupplierContractSet.id.desc()).limit(1)
    )
    if supplier_contract_set:
        context.supplier_contract_set = supplier_contract_set
        context.supplier_contract_record = session.scalar(
            select(SupplierContractRecord)
            .where(SupplierContractRecord.supplier_contract_set_id == supplier_contract_set.supplier_contract_set_id)
            .order_by(SupplierContractRecord.created_at.desc(), SupplierContractRecord.id.desc())
            .limit(1)
        )
        if context.supplier_contract_record:
            context.supplier_contract_obligations = list(
                session.scalars(
                    select(SupplierContractObligation)
                    .where(
                        SupplierContractObligation.supplier_contract_id
                        == context.supplier_contract_record.supplier_contract_id
                    )
                    .order_by(SupplierContractObligation.created_at.asc(), SupplierContractObligation.id.asc())
                )
            )
            context.supplier_contract_comments = list(
                session.scalars(
                    select(SupplierContractComment)
                    .where(
                        SupplierContractComment.supplier_contract_id
                        == context.supplier_contract_record.supplier_contract_id
                    )
                    .order_by(SupplierContractComment.created_at.asc(), SupplierContractComment.id.asc())
                )
            )

    execution_plan_set = session.scalar(
        select(ExecutionPlanSet)
        .where(ExecutionPlanSet.deal_id == deal_id)
        .order_by(ExecutionPlanSet.created_at.desc(), ExecutionPlanSet.id.desc())
        .limit(1)
    )
    if execution_plan_set:
        context.execution_plan_set = execution_plan_set
        context.execution_plan_record = session.scalar(
            select(ExecutionPlanRecord)
            .where(ExecutionPlanRecord.execution_plan_set_id == execution_plan_set.execution_plan_set_id)
            .order_by(ExecutionPlanRecord.created_at.desc(), ExecutionPlanRecord.id.desc())
            .limit(1)
        )
        if context.execution_plan_record:
            context.execution_plan_milestones = list(
                session.scalars(
                    select(ExecutionPlanMilestone)
                    .where(ExecutionPlanMilestone.execution_plan_id == context.execution_plan_record.execution_plan_id)
                    .order_by(ExecutionPlanMilestone.created_at.asc(), ExecutionPlanMilestone.id.asc())
                )
            )
            context.execution_plan_assumptions = list(
                session.scalars(
                    select(ExecutionPlanAssumption)
                    .where(ExecutionPlanAssumption.execution_plan_id == context.execution_plan_record.execution_plan_id)
                    .order_by(ExecutionPlanAssumption.created_at.asc(), ExecutionPlanAssumption.id.asc())
                )
            )

    purchase_order_query = select(PurchaseOrderSet).where(PurchaseOrderSet.deal_id == deal_id)
    if supplier_id:
        purchase_order_query = purchase_order_query.where(PurchaseOrderSet.supplier_id == supplier_id)
    purchase_order_set = session.scalar(
        purchase_order_query.order_by(PurchaseOrderSet.created_at.desc(), PurchaseOrderSet.id.desc()).limit(1)
    )
    if purchase_order_set:
        context.purchase_order_set = purchase_order_set
        context.purchase_order_record = session.scalar(
            select(PurchaseOrderRecord)
            .where(PurchaseOrderRecord.purchase_order_set_id == purchase_order_set.purchase_order_set_id)
            .order_by(PurchaseOrderRecord.created_at.desc(), PurchaseOrderRecord.id.desc())
            .limit(1)
        )
        if context.purchase_order_record:
            context.purchase_order_items = list(
                session.scalars(
                    select(PurchaseOrderItem)
                    .where(PurchaseOrderItem.purchase_order_id == context.purchase_order_record.purchase_order_id)
                    .order_by(PurchaseOrderItem.created_at.asc(), PurchaseOrderItem.id.asc())
                )
            )
            context.purchase_order_links = list(
                session.scalars(
                    select(PurchaseOrderLink)
                    .where(PurchaseOrderLink.purchase_order_id == context.purchase_order_record.purchase_order_id)
                    .order_by(PurchaseOrderLink.created_at.asc(), PurchaseOrderLink.id.asc())
                )
            )

    delivery_milestone_set = session.scalar(
        select(DeliveryMilestoneSet)
        .where(DeliveryMilestoneSet.deal_id == deal_id)
        .order_by(DeliveryMilestoneSet.created_at.desc(), DeliveryMilestoneSet.id.desc())
        .limit(1)
    )
    if delivery_milestone_set:
        context.delivery_milestone_set = delivery_milestone_set
        for milestone in session.scalars(
            select(DeliveryMilestoneRecord)
            .where(DeliveryMilestoneRecord.delivery_milestone_set_id == delivery_milestone_set.delivery_milestone_set_id)
            .order_by(DeliveryMilestoneRecord.created_at.asc(), DeliveryMilestoneRecord.id.asc())
        ):
            events = list(
                session.scalars(
                    select(DeliveryMilestoneEvent)
                    .where(DeliveryMilestoneEvent.delivery_milestone_id == milestone.delivery_milestone_id)
                    .order_by(DeliveryMilestoneEvent.event_timestamp.asc(), DeliveryMilestoneEvent.id.asc())
                )
            )
            context.delivery_milestones.append((milestone, events))

    if supplier_id:
        fulfillment_set = session.scalar(
            select(SupplierFulfillmentSet)
            .where(SupplierFulfillmentSet.deal_id == deal_id)
            .order_by(SupplierFulfillmentSet.created_at.desc(), SupplierFulfillmentSet.id.desc())
            .limit(1)
        )
        if fulfillment_set:
            fulfillment_record = session.scalar(
                select(SupplierFulfillmentRecord)
                .where(
                    SupplierFulfillmentRecord.supplier_fulfillment_set_id == fulfillment_set.supplier_fulfillment_set_id,
                    SupplierFulfillmentRecord.supplier_id == supplier_id,
                )
                .order_by(SupplierFulfillmentRecord.created_at.desc(), SupplierFulfillmentRecord.id.desc())
                .limit(1)
            )
            if fulfillment_record:
                context.supplier_fulfillment_set = fulfillment_set
                context.supplier_fulfillment_record = fulfillment_record
                context.supplier_fulfillment_events = list(
                    session.scalars(
                        select(SupplierFulfillmentEvent)
                        .where(
                            SupplierFulfillmentEvent.supplier_fulfillment_id
                            == fulfillment_record.supplier_fulfillment_id
                        )
                        .order_by(SupplierFulfillmentEvent.event_timestamp.asc(), SupplierFulfillmentEvent.id.asc())
                    )
                )

    return context
