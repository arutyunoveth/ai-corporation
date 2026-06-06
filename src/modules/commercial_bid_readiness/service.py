from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.bid_completeness.models import BidCompletenessSet
from src.modules.bid_completeness.schemas import CheckBidCompletenessRequest
from src.modules.bid_completeness.service import check_bid_completeness, get_bid_completeness_set
from src.modules.bid_documents.models import BidDocumentCollectionSet
from src.modules.bid_documents.schemas import BuildBidDocumentCollectionRequest
from src.modules.bid_documents.service import build_bid_document_collection, get_bid_document_collection_set
from src.modules.bid_packages.models import BidPackageSet
from src.modules.bid_packages.schemas import BuildBidPackageRequest
from src.modules.bid_packages.service import build_bid_package, get_bid_package_set
from src.modules.cash_gap.models import CashGapSet
from src.modules.cash_gap.schemas import BuildCashGapRequest
from src.modules.cash_gap.service import build_cash_gap, get_cash_gap_set
from src.modules.ceo_approval.models import CEOApprovalSet
from src.modules.ceo_approval.schemas import (
    BuildCEOApprovalRequest,
    CEOApprovalConditionInput,
    RecordCEODecisionRequest,
)
from src.modules.ceo_approval.service import build_ceo_approval, get_ceo_approval_set, record_ceo_decision
from src.modules.commercial_bid_readiness.schemas import (
    BuildCommercialBidReadinessRequest,
    BuildCommercialSupplierRequestDraftRequest,
    CommercialBidWorkspaceActionRequest,
    CommercialBidWorkspaceActionResponse,
    CommercialManualTKPBatchResponse,
    CommercialSupplierRequestDraftResponse,
    CommercialWorkspaceSnapshotResponse,
    RegisterCommercialTKPBatchRequest,
)
from src.modules.compliance_matrix.models import ComplianceMatrix
from src.modules.contract_risks.models import ContractRiskSet
from src.modules.contract_risks.schemas import BuildContractRiskRequest
from src.modules.contract_risks.service import build_contract_risks, get_contract_risk_set
from src.modules.cost_model.models import CostModelSet
from src.modules.cost_model.schemas import BuildCostModelRequest
from src.modules.cost_model.service import build_cost_model, get_cost_model_set
from src.modules.deal_registry.models import Deal
from src.modules.document_ingestion.models import DocumentSet
from src.modules.document_requirements.models import DocumentRequirementRow, DocumentRequirementSet
from src.modules.document_store.schemas import CreateArtifactRequest
from src.modules.document_store.service import create_artifact
from src.modules.event_log.models import DecisionRecord, EventRecord
from src.modules.event_log.schemas import AppendDecisionRequest, AppendEventRequest
from src.modules.event_log.service import append_decision, append_event, append_event_record
from src.modules.finance_memo.models import FinanceMemoSet
from src.modules.finance_memo.schemas import BuildFinanceMemoRequest
from src.modules.finance_memo.service import build_finance_memo, get_finance_memo_set
from src.modules.financing_strategy.models import FinancingStrategySet
from src.modules.financing_strategy.schemas import BuildFinancingStrategyRequest
from src.modules.financing_strategy.service import build_financing_strategy, get_financing_strategy_set
from src.modules.initial_tech_risks.models import InitialTechRiskFlag, InitialTechRiskFlagSet
from src.modules.integrated_risk_memo.models import IntegratedRiskMemoSet
from src.modules.integrated_risk_memo.schemas import BuildIntegratedRiskMemoRequest
from src.modules.integrated_risk_memo.service import build_integrated_risk_memo, get_integrated_risk_memo_set
from src.modules.quote_comparison.models import QuoteComparisonRecommendation, QuoteComparisonRow, QuoteComparisonSet
from src.modules.quote_comparison.schemas import BuildQuoteComparisonRequest
from src.modules.quote_comparison.service import build_quote_comparison, get_quote_comparison_set
from src.modules.quote_repository.models import QuoteRecord, QuoteSet
from src.modules.quote_repository.schemas import RegisterQuoteRequest
from src.modules.quote_repository.service import get_quote_set, register_quote
from src.modules.requirement_extraction.models import RequirementExtractionRecord, RequirementExtractionSet
from src.modules.rfq_generator.models import RFQBatch
from src.modules.rfq_generator.schemas import BuildRFQBatchRequest
from src.modules.rfq_generator.service import build_rfq_batch, get_rfq_batch
from src.modules.status_engine.models import DealStatusHistory
from src.modules.submission_readiness.models import SubmissionReadinessSet
from src.modules.submission_readiness.schemas import BuildSubmissionReadinessRequest
from src.modules.submission_readiness.service import build_submission_readiness, get_submission_readiness_set
from src.modules.supplier_communications.models import SupplierCommunicationSet, SupplierCommunicationThread
from src.modules.supplier_communications.schemas import BuildSupplierCommunicationSetRequest, RecordSupplierMessageRequest
from src.modules.supplier_communications.service import (
    build_supplier_communication_set,
    get_supplier_communication_set,
    record_supplier_message,
)
from src.modules.supplier_registry.schemas import (
    CreateSupplierContactRequest,
    CreateSupplierRequest,
    CreateSupplierTagRequest,
)
from src.modules.supplier_registry.service import add_supplier_contact, add_supplier_tag, create_supplier
from src.modules.supplier_search.models import SupplierShortlist, SupplierShortlistRow
from src.modules.supplier_search.schemas import BuildSupplierShortlistRequest
from src.modules.supplier_search.service import build_supplier_shortlist, get_supplier_shortlist
from src.modules.supplier_verification.models import SupplierVerificationSet
from src.modules.supplier_verification.schemas import BuildSupplierVerificationRequest
from src.modules.supplier_verification.service import build_supplier_verification, get_supplier_verification_set
from src.modules.tender_intake.models import TenderIntakeRecord
from src.modules.tender_summary.models import TenderSummary
from src.shared.db.base import utcnow
from src.shared.enums import (
    ApprovalDecision,
    ArtifactType,
    DecisionByType,
    EventSeverity,
    MessageDirection,
    ReadinessRecommendation,
)
from src.shared.errors import NotFoundError, ValidationError


def _latest(session: Session, model, *conditions):
    return session.scalar(select(model).where(*conditions).order_by(model.created_at.desc(), model.id.desc()).limit(1))


def _load_deal(session: Session, deal_id: str) -> Deal:
    deal = session.scalar(select(Deal).where(Deal.deal_id == deal_id, Deal.is_deleted.is_(False)))
    if not deal:
        raise NotFoundError(f"Deal '{deal_id}' was not found")
    return deal


def _load_context(session: Session, deal_id: str) -> dict:
    deal = _load_deal(session, deal_id)
    intake = _latest(session, TenderIntakeRecord, TenderIntakeRecord.deal_id == deal_id)
    document_set = _latest(session, DocumentSet, DocumentSet.deal_id == deal_id)
    summary = _latest(session, TenderSummary, TenderSummary.deal_id == deal_id)
    compliance = _latest(session, ComplianceMatrix, ComplianceMatrix.deal_id == deal_id)
    requirement_set = _latest(session, RequirementExtractionSet, RequirementExtractionSet.document_set_id == document_set.document_set_id) if document_set else None
    requirement_records = (
        list(
            session.scalars(
                select(RequirementExtractionRecord)
                .where(RequirementExtractionRecord.requirement_extraction_set_id == requirement_set.requirement_extraction_set_id)
                .order_by(RequirementExtractionRecord.created_at.asc(), RequirementExtractionRecord.id.asc())
            )
        )
        if requirement_set
        else []
    )
    document_requirement_set = _latest(session, DocumentRequirementSet, DocumentRequirementSet.deal_id == deal_id)
    document_requirement_rows = (
        list(
            session.scalars(
                select(DocumentRequirementRow)
                .where(DocumentRequirementRow.document_requirement_set_id == document_requirement_set.document_requirement_set_id)
                .order_by(DocumentRequirementRow.sequence_no.asc(), DocumentRequirementRow.id.asc())
            )
        )
        if document_requirement_set
        else []
    )
    tech_risk_set = _latest(session, InitialTechRiskFlagSet, InitialTechRiskFlagSet.deal_id == deal_id)
    tech_risk_flags = (
        list(
            session.scalars(
                select(InitialTechRiskFlag)
                .where(InitialTechRiskFlag.risk_flag_set_id == tech_risk_set.risk_flag_set_id)
                .order_by(InitialTechRiskFlag.created_at.asc(), InitialTechRiskFlag.id.asc())
            )
        )
        if tech_risk_set
        else []
    )
    if not all([intake, document_set, summary, document_requirement_set, tech_risk_set]):
        raise ValidationError("Commercial workspace requires the persisted pre-bid demo baseline before TKP/economics steps")
    return {
        "deal": deal,
        "intake": intake,
        "document_set": document_set,
        "summary": summary,
        "compliance": compliance,
        "requirement_set": requirement_set,
        "requirement_records": requirement_records,
        "document_requirement_set": document_requirement_set,
        "document_requirement_rows": document_requirement_rows,
        "tech_risk_set": tech_risk_set,
        "tech_risk_flags": tech_risk_flags,
    }


def _supplier_request_payload(context: dict) -> tuple[str, str, list[str], dict]:
    summary = context["summary"]
    requirement_records = context["requirement_records"]
    document_requirement_rows = context["document_requirement_rows"]
    tech_risk_flags = context["tech_risk_flags"]
    procurement_number = summary.structured_summary_json.get("procurement_number") or context["deal"].procurement_number or "n/a"
    customer_name = summary.structured_summary_json.get("customer_name") or context["deal"].customer_name or "n/a"
    title = summary.structured_summary_json.get("title") or context["deal"].title

    technical_points = [
        record.requirement_text for record in requirement_records[:4]
    ] + [row.requirement_title for row in document_requirement_rows[:4]]
    questions = [
        f"Confirm compliance with: {row.requirement_title}"
        for row in document_requirement_rows
        if row.requires_manual_review or str(row.requirement_status) in {"REQUIRED", "CONDITIONAL"}
    ][:6]
    if not questions:
        questions = [f"Confirm commercial and technical fit for {title}."]
    if tech_risk_flags:
        questions.append(f"Clarify mitigation for key risk: {tech_risk_flags[0].summary}")

    body = (
        f"Internal draft supplier request for procurement {procurement_number} ({title}).\n\n"
        f"Customer: {customer_name}\n"
        "Purpose: collect manual TKP / commercial quotes for human-reviewed bid preparation.\n"
        "Restrictions: no automatic outbound email is sent from the system; operator delivery remains manual.\n\n"
        "Technical scope highlights:\n"
        + "\n".join(f"- {item}" for item in technical_points[:6])
        + "\n\nSupplier questions:\n"
        + "\n".join(f"- {item}" for item in questions)
    )
    subject = f"Manual TKP request draft for {procurement_number}"
    based_on = {
        "tender_summary_id": summary.tender_summary_id,
        "document_requirement_set_id": context["document_requirement_set"].document_requirement_set_id,
        "initial_tech_risk_flag_set_id": context["tech_risk_set"].risk_flag_set_id,
    }
    return subject, body, questions, based_on


def build_supplier_request_draft(
    session: Session,
    deal_id: str,
    payload: BuildCommercialSupplierRequestDraftRequest,
) -> CommercialSupplierRequestDraftResponse:
    context = _load_context(session, deal_id)
    subject, body, questions, based_on = _supplier_request_payload(context)
    append_event_record(
        session,
        deal_id=deal_id,
        event_code="commercial_supplier_request_drafted",
        source_module_id="C5",
        severity=EventSeverity.INFO,
        payload_json={
            "operator_ref": payload.operator_ref,
            "question_count": len(questions),
            "based_on": based_on,
        },
    )
    session.commit()
    return CommercialSupplierRequestDraftResponse(
        deal_id=deal_id,
        generated_at=datetime.now(UTC),
        request_subject=subject,
        request_body=body,
        supplier_questions=questions,
        based_on=based_on,
    )


def _ensure_manual_shortlist_rows(
    session: Session,
    *,
    shortlist_id: str,
    supplier_ids: list[str],
) -> None:
    shortlist, rows = get_supplier_shortlist(session, shortlist_id)
    existing_ids = {row.supplier_id for row in rows}
    next_rank = max((row.rank_order for row in rows), default=0) + 1
    created = 0
    for supplier_id in supplier_ids:
        if supplier_id in existing_ids:
            continue
        session.add(
            SupplierShortlistRow(
                supplier_shortlist_id=shortlist.supplier_shortlist_id,
                supplier_id=supplier_id,
                rank_order=next_rank,
                inclusion_reason="Manual TKP registration requested by commercial operator.",
                source_type="MANUAL_TKP",
            )
        )
        existing_ids.add(supplier_id)
        next_rank += 1
        created += 1
    if created:
        shortlist.updated_at = utcnow()
        session.add(shortlist)
        append_event_record(
            session,
            deal_id=shortlist.deal_id,
            event_code="supplier_shortlist_built",
            source_module_id="M-016",
            severity=EventSeverity.INFO,
            payload_json={
                "supplier_shortlist_id": shortlist.supplier_shortlist_id,
                "manual_rows_added": created,
            },
        )
        session.commit()


def register_manual_tkp_batch(
    session: Session,
    deal_id: str,
    payload: RegisterCommercialTKPBatchRequest,
) -> CommercialManualTKPBatchResponse:
    context = _load_context(session, deal_id)
    subject, body, questions, _based_on = _supplier_request_payload(context)

    supplier_inputs: list[tuple[str, object]] = []
    created_supplier_ids: list[str] = []
    for item in payload.suppliers:
        supplier, _duplicate = create_supplier(
            session,
            CreateSupplierRequest(
                legal_name=item.legal_name,
                display_name=item.display_name,
                inn=item.inn,
                country_code=item.country_code,
                notes=item.notes,
            ),
        )
        created_supplier_ids.append(supplier.supplier_id)
        supplier_inputs.append((supplier.supplier_id, item))
        add_supplier_contact(
            session,
            supplier.supplier_id,
            CreateSupplierContactRequest(
                contact_name=item.contact_name,
                email=item.contact_email,
                phone=item.contact_phone,
                is_primary=True,
            ),
        )
        tags = {tag.strip().upper() for tag in item.tags if tag.strip()}
        tags.add("TENDER_READY")
        tags.add(str(context["deal"].domain_type).upper())
        for tag in sorted(tags):
            add_supplier_tag(session, supplier.supplier_id, CreateSupplierTagRequest(tag_code=tag))

    shortlist = build_supplier_shortlist(
        session,
        BuildSupplierShortlistRequest(
            deal_id=deal_id,
            intake_id=context["intake"].intake_id,
            document_set_id=context["document_set"].document_set_id,
            tender_summary_id=context["summary"].tender_summary_id,
            compliance_matrix_id=context["compliance"].compliance_matrix_id if context["compliance"] else None,
            document_requirement_set_id=context["document_requirement_set"].document_requirement_set_id,
            risk_flag_set_id=context["tech_risk_set"].risk_flag_set_id,
        ),
    )
    _ensure_manual_shortlist_rows(
        session,
        shortlist_id=shortlist.supplier_shortlist_id,
        supplier_ids=created_supplier_ids,
    )
    rfq_batch = build_rfq_batch(
        session,
        BuildRFQBatchRequest(
            deal_id=deal_id,
            supplier_shortlist_id=shortlist.supplier_shortlist_id,
        ),
    )
    communication_set = build_supplier_communication_set(
        session,
        BuildSupplierCommunicationSetRequest(
            deal_id=deal_id,
            rfq_batch_id=rfq_batch.rfq_batch_id,
        ),
    )
    _set, threads = get_supplier_communication_set(session, communication_set.supplier_communication_set_id)
    thread_map = {thread.supplier_id: thread for thread, _messages in threads}
    _batch, rfq_entries = get_rfq_batch(session, rfq_batch.rfq_batch_id)
    rfq_map = {rfq.supplier_id: rfq for rfq, _artifact_refs in rfq_entries}

    quote_ids: list[str] = []
    quote_set_id: str | None = None
    for supplier_id, item in supplier_inputs:
        thread = thread_map.get(supplier_id)
        rfq = rfq_map.get(supplier_id)
        if thread is None or rfq is None:
            raise ValidationError(f"Supplier '{supplier_id}' is missing RFQ/thread bindings for manual TKP registration")
        record_supplier_message(
            session,
            thread.supplier_thread_id,
            RecordSupplierMessageRequest(
                direction=MessageDirection.OUTBOUND,
                message_subject=subject,
                message_text=body + "\n\nOperator-copied questions:\n" + "\n".join(f"- {question}" for question in questions),
            ),
        )
        quote_artifact = create_artifact(
            session,
            CreateArtifactRequest(
                deal_id=deal_id,
                artifact_type=ArtifactType.SUPPLIER_QUOTE,
                file_name=f"{item.display_name.lower().replace(' ', '-')}-quote.txt",
                mime_type="text/plain",
                storage_uri=f"demo://commercial-workspace/{deal_id}/{item.inn}/quote.txt",
                checksum_sha256=f"commercial-workspace-{item.inn}-quote",
            ),
        )
        quote = register_quote(
            session,
            RegisterQuoteRequest(
                deal_id=deal_id,
                supplier_id=supplier_id,
                rfq_id=rfq.rfq_id,
                supplier_thread_id=thread.supplier_thread_id,
                quoted_amount=item.quoted_amount,
                currency_code=item.currency_code,
                notes=item.notes,
                artifact_refs=[quote_artifact.artifact_ref],
            ),
        )
        quote_ids.append(quote.quote_id)
        quote_set_id = quote.quote_set_id

    append_event_record(
        session,
        deal_id=deal_id,
        event_code="commercial_tkp_manual_registered",
        source_module_id="C5",
        severity=EventSeverity.INFO,
        payload_json={
            "operator_ref": payload.operator_ref,
            "supplier_shortlist_id": shortlist.supplier_shortlist_id,
            "rfq_batch_id": rfq_batch.rfq_batch_id,
            "supplier_communication_set_id": communication_set.supplier_communication_set_id,
            "quote_count": len(quote_ids),
        },
    )
    session.commit()
    if quote_set_id is None:
        raise ValidationError("Manual TKP registration did not produce a formal quote set")
    return CommercialManualTKPBatchResponse(
        deal_id=deal_id,
        supplier_ids=created_supplier_ids,
        quote_ids=quote_ids,
        supplier_shortlist_id=shortlist.supplier_shortlist_id,
        rfq_batch_id=rfq_batch.rfq_batch_id,
        supplier_communication_set_id=communication_set.supplier_communication_set_id,
        quote_set_id=quote_set_id,
        registered_at=datetime.now(UTC),
    )


def _build_readiness_artifacts(session: Session, deal_id: str) -> dict:
    context = _load_context(session, deal_id)
    shortlist = _latest(session, SupplierShortlist, SupplierShortlist.deal_id == deal_id)
    quote_set = _latest(session, QuoteSet, QuoteSet.deal_id == deal_id)
    contract_risk_set = _latest(session, ContractRiskSet, ContractRiskSet.deal_id == deal_id)
    if not shortlist or not quote_set:
        raise ValidationError("Commercial readiness requires a supplier shortlist and formal quote set. Register manual TKP first.")
    if not contract_risk_set:
        contract_risk_set = build_contract_risks(
            session,
            BuildContractRiskRequest(
                deal_id=deal_id,
                document_set_id=context["document_set"].document_set_id,
            ),
        )

    verification_set = build_supplier_verification(
        session,
        BuildSupplierVerificationRequest(
            deal_id=deal_id,
            supplier_shortlist_id=shortlist.supplier_shortlist_id,
        ),
    )
    comparison_set = build_quote_comparison(
        session,
        BuildQuoteComparisonRequest(
            deal_id=deal_id,
            quote_set_id=quote_set.quote_set_id,
            supplier_verification_set_id=verification_set.supplier_verification_set_id,
        ),
    )
    cost_model_set = build_cost_model(
        session,
        BuildCostModelRequest(
            deal_id=deal_id,
            quote_comparison_set_id=comparison_set.quote_comparison_set_id,
        ),
    )
    cash_gap_set = build_cash_gap(
        session,
        BuildCashGapRequest(
            deal_id=deal_id,
            cost_model_set_id=cost_model_set.cost_model_set_id,
        ),
    )
    financing_strategy_set = build_financing_strategy(
        session,
        BuildFinancingStrategyRequest(
            deal_id=deal_id,
            cash_gap_set_id=cash_gap_set.cash_gap_set_id,
        ),
    )
    finance_memo_set = build_finance_memo(
        session,
        BuildFinanceMemoRequest(
            deal_id=deal_id,
            cost_model_set_id=cost_model_set.cost_model_set_id,
            cash_gap_set_id=cash_gap_set.cash_gap_set_id,
            financing_strategy_set_id=financing_strategy_set.financing_strategy_set_id,
        ),
    )
    integrated_risk_memo_set = build_integrated_risk_memo(
        session,
        BuildIntegratedRiskMemoRequest(
            deal_id=deal_id,
            initial_tech_risk_flag_set_id=context["tech_risk_set"].risk_flag_set_id,
            supplier_verification_set_id=verification_set.supplier_verification_set_id,
            quote_comparison_set_id=comparison_set.quote_comparison_set_id,
            finance_memo_set_id=finance_memo_set.finance_memo_set_id,
            contract_risk_set_id=contract_risk_set.contract_risk_set_id,
        ),
    )
    ceo_approval_set = build_ceo_approval(
        session,
        BuildCEOApprovalRequest(
            deal_id=deal_id,
            finance_memo_set_id=finance_memo_set.finance_memo_set_id,
            integrated_risk_memo_set_id=integrated_risk_memo_set.integrated_risk_memo_set_id,
        ),
    )
    bid_document_collection_set = build_bid_document_collection(
        session,
        BuildBidDocumentCollectionRequest(
            deal_id=deal_id,
            document_requirement_set_id=context["document_requirement_set"].document_requirement_set_id,
            ceo_approval_set_id=ceo_approval_set.ceo_approval_set_id,
        ),
    )
    bid_package_set = build_bid_package(
        session,
        BuildBidPackageRequest(
            deal_id=deal_id,
            bid_document_collection_set_id=bid_document_collection_set.bid_document_collection_set_id,
        ),
    )
    bid_completeness_set = check_bid_completeness(
        session,
        CheckBidCompletenessRequest(
            deal_id=deal_id,
            bid_package_set_id=bid_package_set.bid_package_set_id,
            document_requirement_set_id=context["document_requirement_set"].document_requirement_set_id,
        ),
    )
    submission_readiness_set = build_submission_readiness(
        session,
        BuildSubmissionReadinessRequest(
            deal_id=deal_id,
            bid_completeness_set_id=bid_completeness_set.bid_completeness_set_id,
            ceo_approval_set_id=ceo_approval_set.ceo_approval_set_id,
            finance_memo_set_id=finance_memo_set.finance_memo_set_id,
            integrated_risk_memo_set_id=integrated_risk_memo_set.integrated_risk_memo_set_id,
        ),
    )
    return {
        "context": context,
        "supplier_shortlist": shortlist,
        "quote_set": quote_set,
        "supplier_verification_set": verification_set,
        "quote_comparison_set": comparison_set,
        "cost_model_set": cost_model_set,
        "cash_gap_set": cash_gap_set,
        "financing_strategy_set": financing_strategy_set,
        "finance_memo_set": finance_memo_set,
        "contract_risk_set": contract_risk_set,
        "integrated_risk_memo_set": integrated_risk_memo_set,
        "ceo_approval_set": ceo_approval_set,
        "bid_document_collection_set": bid_document_collection_set,
        "bid_package_set": bid_package_set,
        "bid_completeness_set": bid_completeness_set,
        "submission_readiness_set": submission_readiness_set,
    }


def _build_workspace_snapshot(session: Session, deal_id: str) -> CommercialWorkspaceSnapshotResponse:
    context = _load_context(session, deal_id)
    subject, body, questions, based_on = _supplier_request_payload(context)
    shortlist = _latest(session, SupplierShortlist, SupplierShortlist.deal_id == deal_id)
    quote_set = _latest(session, QuoteSet, QuoteSet.deal_id == deal_id)
    verification_set = _latest(session, SupplierVerificationSet, SupplierVerificationSet.deal_id == deal_id)
    comparison_set = _latest(session, QuoteComparisonSet, QuoteComparisonSet.deal_id == deal_id)
    cost_model_set = _latest(session, CostModelSet, CostModelSet.deal_id == deal_id)
    cash_gap_set = _latest(session, CashGapSet, CashGapSet.deal_id == deal_id)
    financing_strategy_set = _latest(session, FinancingStrategySet, FinancingStrategySet.deal_id == deal_id)
    finance_memo_set = _latest(session, FinanceMemoSet, FinanceMemoSet.deal_id == deal_id)
    contract_risk_set = _latest(session, ContractRiskSet, ContractRiskSet.deal_id == deal_id)
    integrated_risk_memo_set = _latest(session, IntegratedRiskMemoSet, IntegratedRiskMemoSet.deal_id == deal_id)
    ceo_approval_set = _latest(session, CEOApprovalSet, CEOApprovalSet.deal_id == deal_id)
    bid_document_collection_set = _latest(session, BidDocumentCollectionSet, BidDocumentCollectionSet.deal_id == deal_id)
    bid_package_set = _latest(session, BidPackageSet, BidPackageSet.deal_id == deal_id)
    bid_completeness_set = _latest(session, BidCompletenessSet, BidCompletenessSet.deal_id == deal_id)
    submission_readiness_set = _latest(session, SubmissionReadinessSet, SubmissionReadinessSet.deal_id == deal_id)
    recent_decisions = list(
        session.scalars(
            select(DecisionRecord)
            .where(DecisionRecord.deal_id == deal_id)
            .order_by(DecisionRecord.created_at.desc(), DecisionRecord.id.desc())
            .limit(8)
        )
    )
    recent_events = list(
        session.scalars(
            select(EventRecord)
            .where(EventRecord.deal_id == deal_id)
            .order_by(EventRecord.created_at.desc(), EventRecord.id.desc())
            .limit(10)
        )
    )

    quote_rows = []
    quote_comparison_summary = {}
    if comparison_set:
        _set, rows, recommendation = get_quote_comparison_set(session, comparison_set.quote_comparison_set_id)
        quote_rows = rows
        quote_comparison_summary = {
            "quote_comparison_set_id": comparison_set.quote_comparison_set_id,
            "recommended_supplier_id": recommendation.recommended_supplier_id if recommendation else None,
            "recommended_quote_id": recommendation.recommended_quote_id if recommendation else None,
            "rationale": recommendation.rationale if recommendation else None,
            "ranked_quotes": [
                {
                    "supplier_id": row.supplier_id,
                    "quote_id": row.quote_id,
                    "total_score": row.total_score,
                    "rank_order": row.rank_order,
                }
                for row in rows
            ],
        }

    economics_summary = {}
    if finance_memo_set and cost_model_set and cash_gap_set and financing_strategy_set:
        _cost_set, cost_records = get_cost_model_set(session, cost_model_set.cost_model_set_id)
        _cash_set, cash_records = get_cash_gap_set(session, cash_gap_set.cash_gap_set_id)
        _strategy_set, strategy_records = get_financing_strategy_set(session, financing_strategy_set.financing_strategy_set_id)
        _finance_set, finance_records = get_finance_memo_set(session, finance_memo_set.finance_memo_set_id)
        cost_record, _cost_lines = cost_records[0]
        cash_record, _cash_scenarios = cash_records[0]
        strategy_record, strategy_options = strategy_records[0]
        finance_record, finance_flags = finance_records[0]
        economics_summary = {
            "cost_model_set_id": cost_model_set.cost_model_set_id,
            "cash_gap_set_id": cash_gap_set.cash_gap_set_id,
            "financing_strategy_set_id": financing_strategy_set.financing_strategy_set_id,
            "finance_memo_set_id": finance_memo_set.finance_memo_set_id,
            "total_cost": cost_record.total_cost,
            "min_viable_bid": cost_record.min_viable_bid,
            "peak_cash_gap_amount": cash_record.peak_gap_amount,
            "cash_gap_duration_days": cash_record.gap_duration_days,
            "recommended_financing_option": strategy_record.recommended_option_code,
            "finance_recommendation": str(finance_record.recommendation),
            "finance_flags": [flag.summary for flag in finance_flags],
            "financing_options": [
                {
                    "option_code": option.option_code,
                    "funding_amount": option.funding_amount,
                    "funding_cost": option.funding_cost,
                    "feasibility_status": str(option.feasibility_status),
                }
                for option in strategy_options
            ],
        }

    readiness_summary = {}
    if submission_readiness_set and bid_completeness_set and ceo_approval_set:
        _readiness_set, readiness_records = get_submission_readiness_set(session, submission_readiness_set.submission_readiness_set_id)
        _completeness_set, completeness_records, readiness_reports = get_bid_completeness_set(
            session, bid_completeness_set.bid_completeness_set_id
        )
        _approval_set, approval_records = get_ceo_approval_set(session, ceo_approval_set.ceo_approval_set_id)
        readiness_record, readiness_flags = readiness_records[0]
        completeness_record, completeness_flags = completeness_records[0]
        latest_approval = approval_records[-1][0] if approval_records else None
        readiness_summary = {
            "ceo_approval_set_id": ceo_approval_set.ceo_approval_set_id,
            "latest_ceo_decision": str(latest_approval.decision) if latest_approval else None,
            "bid_document_collection_set_id": bid_document_collection_set.bid_document_collection_set_id if bid_document_collection_set else None,
            "bid_package_set_id": bid_package_set.bid_package_set_id if bid_package_set else None,
            "bid_completeness_set_id": bid_completeness_set.bid_completeness_set_id,
            "submission_readiness_set_id": submission_readiness_set.submission_readiness_set_id,
            "submission_readiness_status": str(submission_readiness_set.readiness_status),
            "submission_recommendation": str(readiness_record.recommendation),
            "submission_flags": [flag.summary for flag in readiness_flags],
            "completeness_status": str(bid_completeness_set.completeness_status),
            "completeness_summary": completeness_record.summary_text,
            "completeness_flags": [flag.summary for flag in completeness_flags],
            "blocking_issue_count": readiness_reports[0].blocking_issue_count if readiness_reports else 0,
        }

    quote_summary = []
    if quote_set:
        _quote_set, quotes = get_quote_set(session, quote_set.quote_set_id)
        quote_summary = [
            {
                "quote_id": quote.quote_id,
                "supplier_id": quote.supplier_id,
                "quoted_amount": quote.quoted_amount,
                "currency_code": quote.currency_code,
                "quote_status": str(quote.quote_status),
            }
            for quote, _bindings in quotes
        ]

    executive_report_json = {
        "deal_id": deal_id,
        "supplier_request_draft": {
            "subject": subject,
            "based_on": based_on,
            "supplier_questions": questions,
        },
        "tkp_summary": {
            "supplier_shortlist_id": shortlist.supplier_shortlist_id if shortlist else None,
            "quote_set_id": quote_set.quote_set_id if quote_set else None,
            "quotes": quote_summary,
            "quote_comparison": quote_comparison_summary,
        },
        "economics_summary": economics_summary,
        "readiness_summary": readiness_summary,
        "recent_decisions": [
            {
                "decision_code": item.decision_code,
                "decided_by_ref": item.decided_by_ref,
                "rationale": item.rationale,
            }
            for item in recent_decisions
        ],
        "recent_events": [
            {
                "event_code": item.event_code,
                "source_module_id": item.source_module_id,
            }
            for item in recent_events
        ],
        "human_control_policy": "All outputs remain internal, manual-control, and human-reviewable.",
    }
    report_lines = [
        "# Commercial MVP v1 Workspace Report",
        "",
        "## Supplier Request Draft",
        f"- Subject: {subject}",
        f"- Question count: {len(questions)}",
        "- Manual operator delivery only: yes",
        "",
        "## TKP / Quote Summary",
        f"- Supplier shortlist: {shortlist.supplier_shortlist_id if shortlist else 'not built'}",
        f"- Quote set: {quote_set.quote_set_id if quote_set else 'not built'}",
    ]
    for quote in quote_summary:
        report_lines.append(
            f"- Quote {quote['quote_id']} from {quote['supplier_id']}: {quote['quoted_amount']:.2f} {quote['currency_code']} ({quote['quote_status']})"
        )
    report_lines.extend(
        [
            "",
            "## Quote Comparison",
            f"- Comparison set: {quote_comparison_summary.get('quote_comparison_set_id', 'not built')}",
            f"- Recommended supplier: {quote_comparison_summary.get('recommended_supplier_id', 'n/a')}",
            f"- Rationale: {quote_comparison_summary.get('rationale', 'n/a')}",
            "",
            "## Economics",
            f"- Finance memo set: {economics_summary.get('finance_memo_set_id', 'not built')}",
            f"- Total cost: {economics_summary.get('total_cost', 'n/a')}",
            f"- Min viable bid: {economics_summary.get('min_viable_bid', 'n/a')}",
            f"- Peak cash gap: {economics_summary.get('peak_cash_gap_amount', 'n/a')}",
            f"- Finance recommendation: {economics_summary.get('finance_recommendation', 'n/a')}",
            "",
            "## Bid Readiness",
            f"- Submission readiness set: {readiness_summary.get('submission_readiness_set_id', 'not built')}",
            f"- Submission readiness status: {readiness_summary.get('submission_readiness_status', 'n/a')}",
            f"- Submission recommendation: {readiness_summary.get('submission_recommendation', 'n/a')}",
            f"- Completeness status: {readiness_summary.get('completeness_status', 'n/a')}",
            "",
            "## Human Control Boundaries",
            "- No supplier email automation",
            "- No procurement platform submission",
            "- No EDS/signature actions",
            "- Final bid submission remains human-only",
        ]
    )
    return CommercialWorkspaceSnapshotResponse(
        deal_id=deal_id,
        generated_at=datetime.now(UTC),
        latest_ids={
            "supplier_shortlist_id": shortlist.supplier_shortlist_id if shortlist else None,
            "quote_set_id": quote_set.quote_set_id if quote_set else None,
            "supplier_verification_set_id": verification_set.supplier_verification_set_id if verification_set else None,
            "quote_comparison_set_id": comparison_set.quote_comparison_set_id if comparison_set else None,
            "cost_model_set_id": cost_model_set.cost_model_set_id if cost_model_set else None,
            "cash_gap_set_id": cash_gap_set.cash_gap_set_id if cash_gap_set else None,
            "financing_strategy_set_id": financing_strategy_set.financing_strategy_set_id if financing_strategy_set else None,
            "finance_memo_set_id": finance_memo_set.finance_memo_set_id if finance_memo_set else None,
            "contract_risk_set_id": contract_risk_set.contract_risk_set_id if contract_risk_set else None,
            "integrated_risk_memo_set_id": integrated_risk_memo_set.integrated_risk_memo_set_id if integrated_risk_memo_set else None,
            "ceo_approval_set_id": ceo_approval_set.ceo_approval_set_id if ceo_approval_set else None,
            "bid_document_collection_set_id": bid_document_collection_set.bid_document_collection_set_id if bid_document_collection_set else None,
            "bid_package_set_id": bid_package_set.bid_package_set_id if bid_package_set else None,
            "bid_completeness_set_id": bid_completeness_set.bid_completeness_set_id if bid_completeness_set else None,
            "submission_readiness_set_id": submission_readiness_set.submission_readiness_set_id if submission_readiness_set else None,
        },
        supplier_request_draft={
            "subject": subject,
            "body": body,
            "supplier_questions": questions,
            "based_on": based_on,
        },
        tkp_summary=executive_report_json["tkp_summary"],
        economics_summary=economics_summary,
        readiness_summary=readiness_summary,
        executive_report_markdown="\n".join(report_lines),
        executive_report_json=executive_report_json,
    )


def build_commercial_bid_readiness(
    session: Session,
    deal_id: str,
    payload: BuildCommercialBidReadinessRequest,
) -> CommercialWorkspaceSnapshotResponse:
    artifacts = _build_readiness_artifacts(session, deal_id)
    append_event_record(
        session,
        deal_id=deal_id,
        event_code="commercial_economics_built",
        source_module_id="C5",
        severity=EventSeverity.INFO,
        payload_json={
            "operator_ref": payload.operator_ref,
            "quote_comparison_set_id": artifacts["quote_comparison_set"].quote_comparison_set_id,
            "finance_memo_set_id": artifacts["finance_memo_set"].finance_memo_set_id,
        },
    )
    append_event_record(
        session,
        deal_id=deal_id,
        event_code="commercial_bid_readiness_built",
        source_module_id="C5",
        severity=EventSeverity.INFO,
        payload_json={
            "operator_ref": payload.operator_ref,
            "submission_readiness_set_id": artifacts["submission_readiness_set"].submission_readiness_set_id,
            "submission_readiness_status": str(artifacts["submission_readiness_set"].readiness_status),
        },
    )
    session.commit()
    return _build_workspace_snapshot(session, deal_id)


def get_commercial_workspace_snapshot(
    session: Session,
    deal_id: str,
) -> CommercialWorkspaceSnapshotResponse:
    return _build_workspace_snapshot(session, deal_id)


def _record_workspace_decision(
    session: Session,
    *,
    deal_id: str,
    action: str,
    operator_ref: str,
    rationale: str,
    extra_payload: dict | None = None,
) -> tuple[DecisionRecord, EventRecord]:
    decision_code_map = {
        "tkp_needed": "COMMERCIAL_WORKSPACE_TKP_NEEDED",
        "tkp_received": "COMMERCIAL_WORKSPACE_TKP_RECEIVED",
        "economics_reviewed": "COMMERCIAL_WORKSPACE_ECONOMICS_REVIEWED",
        "ready_for_human_submission": "COMMERCIAL_WORKSPACE_READY_FOR_HUMAN_SUBMISSION",
    }
    decision = append_decision(
        session,
        AppendDecisionRequest(
            deal_id=deal_id,
            decision_code=decision_code_map[action],
            decided_by_type=DecisionByType.HUMAN,
            decided_by_ref=operator_ref,
            rationale=rationale,
            payload_json={"action": action, "human_control_policy": "respected", **(extra_payload or {})},
        ),
    )
    event = append_event(
        session,
        AppendEventRequest(
            deal_id=deal_id,
            event_code="commercial_workspace_action_recorded",
            source_module_id="C5",
            severity=EventSeverity.INFO,
            payload_json={"decision_id": decision.decision_id, "action": action, "operator_ref": operator_ref},
        ),
    )
    return decision, event


def record_commercial_workspace_action(
    session: Session,
    deal_id: str,
    payload: CommercialBidWorkspaceActionRequest,
) -> CommercialBidWorkspaceActionResponse:
    _load_deal(session, deal_id)
    if payload.action != "ready_for_human_submission":
        decision, event = _record_workspace_decision(
            session,
            deal_id=deal_id,
            action=payload.action,
            operator_ref=payload.operator_ref,
            rationale=payload.rationale,
        )
        return CommercialBidWorkspaceActionResponse(
            deal_id=deal_id,
            action=payload.action,
            decision_id=decision.decision_id,
            recorded_event_id=event.event_id,
        )

    context = _load_context(session, deal_id)
    ceo_approval_set = _latest(session, CEOApprovalSet, CEOApprovalSet.deal_id == deal_id)
    finance_memo_set = _latest(session, FinanceMemoSet, FinanceMemoSet.deal_id == deal_id)
    integrated_risk_memo_set = _latest(session, IntegratedRiskMemoSet, IntegratedRiskMemoSet.deal_id == deal_id)
    if not ceo_approval_set or not finance_memo_set or not integrated_risk_memo_set:
        raise ValidationError("Ready-for-human-submission requires a built readiness package before action recording")

    approval_decision = payload.approval_decision or ApprovalDecision.GO_WITH_CONDITIONS
    conditions = payload.conditions
    if approval_decision == ApprovalDecision.GO_WITH_CONDITIONS and not conditions:
        conditions = ["Proceed to manual human-controlled submission only after final operator review."]
    approval_record = record_ceo_decision(
        session,
        RecordCEODecisionRequest(
            ceo_approval_set_id=ceo_approval_set.ceo_approval_set_id,
            decision=approval_decision,
            decided_by_ref=payload.operator_ref,
            rationale=payload.rationale,
            conditions=[
                CEOApprovalConditionInput(
                    condition_code=f"COND_{index + 1}",
                    condition_text=condition,
                )
                for index, condition in enumerate(conditions)
            ],
        ),
    )
    bid_document_collection_set = build_bid_document_collection(
        session,
        BuildBidDocumentCollectionRequest(
            deal_id=deal_id,
            document_requirement_set_id=context["document_requirement_set"].document_requirement_set_id,
            ceo_approval_set_id=ceo_approval_set.ceo_approval_set_id,
        ),
    )
    bid_package_set = build_bid_package(
        session,
        BuildBidPackageRequest(
            deal_id=deal_id,
            bid_document_collection_set_id=bid_document_collection_set.bid_document_collection_set_id,
        ),
    )
    bid_completeness_set = check_bid_completeness(
        session,
        CheckBidCompletenessRequest(
            deal_id=deal_id,
            bid_package_set_id=bid_package_set.bid_package_set_id,
            document_requirement_set_id=context["document_requirement_set"].document_requirement_set_id,
        ),
    )
    submission_readiness_set = build_submission_readiness(
        session,
        BuildSubmissionReadinessRequest(
            deal_id=deal_id,
            bid_completeness_set_id=bid_completeness_set.bid_completeness_set_id,
            ceo_approval_set_id=ceo_approval_set.ceo_approval_set_id,
            finance_memo_set_id=finance_memo_set.finance_memo_set_id,
            integrated_risk_memo_set_id=integrated_risk_memo_set.integrated_risk_memo_set_id,
        ),
    )
    _readiness_set, readiness_records = get_submission_readiness_set(session, submission_readiness_set.submission_readiness_set_id)
    readiness_record, _readiness_flags = readiness_records[0]
    if str(readiness_record.recommendation) == str(ReadinessRecommendation.NOT_READY):
        raise ValidationError("Bid package is not ready for human submission; complete the blocking internal checks first")

    decision, event = _record_workspace_decision(
        session,
        deal_id=deal_id,
        action=payload.action,
        operator_ref=payload.operator_ref,
        rationale=payload.rationale,
        extra_payload={
            "ceo_approval_id": approval_record.ceo_approval_id,
            "submission_readiness_set_id": submission_readiness_set.submission_readiness_set_id,
            "submission_readiness_status": str(submission_readiness_set.readiness_status),
        },
    )
    return CommercialBidWorkspaceActionResponse(
        deal_id=deal_id,
        action=payload.action,
        decision_id=decision.decision_id,
        recorded_event_id=event.event_id,
        submission_readiness_set_id=submission_readiness_set.submission_readiness_set_id,
        submission_readiness_status=str(submission_readiness_set.readiness_status),
    )
