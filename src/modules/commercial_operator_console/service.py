import html
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.contract_risks.models import ContractRiskFlag, ContractRiskRecord, ContractRiskSet
from src.modules.deal_registry.models import Deal
from src.modules.document_requirements.models import DocumentRequirementRow, DocumentRequirementSet
from src.modules.event_log.models import DecisionRecord, EventRecord
from src.modules.event_log.schemas import AppendDecisionRequest, AppendEventRequest
from src.modules.event_log.service import append_decision, append_event
from src.modules.initial_tech_risks.models import InitialTechRiskFlag, InitialTechRiskFlagSet
from src.modules.prompt_schema_library.models import PromptSchemaRecord
from src.modules.requirement_extraction.models import RequirementExtractionRecord, RequirementExtractionSet
from src.modules.runtime_control_traces.models import RuntimeControlTrace
from src.modules.tender_summary.models import TenderSummary
from src.modules.commercial_operator_console.schemas import (
    CommercialOperatorActionRequest,
    CommercialOperatorActionResponse,
)
from src.shared.enums import DecisionByType, EventSeverity
from src.shared.errors import NotFoundError


def _latest(session: Session, model, *conditions):
    return session.scalar(select(model).where(*conditions).order_by(model.created_at.desc(), model.id.desc()).limit(1))


def _load_deal(session: Session, deal_id: str) -> Deal:
    deal = session.scalar(select(Deal).where(Deal.deal_id == deal_id, Deal.is_deleted.is_(False)))
    if not deal:
        raise NotFoundError(f"Deal '{deal_id}' was not found")
    return deal


def _load_snapshot(session: Session, deal_id: str) -> dict:
    deal = _load_deal(session, deal_id)
    summary = _latest(session, TenderSummary, TenderSummary.deal_id == deal_id)
    req_set = _latest(session, RequirementExtractionSet, RequirementExtractionSet.document_set_id == summary.document_set_id) if summary else None
    req_records = (
        list(
            session.scalars(
                select(RequirementExtractionRecord)
                .where(RequirementExtractionRecord.requirement_extraction_set_id == req_set.requirement_extraction_set_id)
                .order_by(RequirementExtractionRecord.created_at.asc(), RequirementExtractionRecord.id.asc())
            )
        )
        if req_set
        else []
    )
    doc_req_set = _latest(session, DocumentRequirementSet, DocumentRequirementSet.deal_id == deal_id)
    doc_req_rows = (
        list(
            session.scalars(
                select(DocumentRequirementRow)
                .where(DocumentRequirementRow.document_requirement_set_id == doc_req_set.document_requirement_set_id)
                .order_by(DocumentRequirementRow.sequence_no.asc(), DocumentRequirementRow.id.asc())
            )
        )
        if doc_req_set
        else []
    )
    tech_risk_set = _latest(session, InitialTechRiskFlagSet, InitialTechRiskFlagSet.deal_id == deal_id)
    tech_risk_rows = (
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
    contract_risk_set = _latest(session, ContractRiskSet, ContractRiskSet.deal_id == deal_id)
    contract_risk_rows = []
    if contract_risk_set:
        for record in session.scalars(
            select(ContractRiskRecord)
            .where(ContractRiskRecord.contract_risk_set_id == contract_risk_set.contract_risk_set_id)
            .order_by(ContractRiskRecord.created_at.asc(), ContractRiskRecord.id.asc())
        ):
            flags = list(
                session.scalars(
                    select(ContractRiskFlag)
                    .where(ContractRiskFlag.contract_risk_id == record.contract_risk_id)
                    .order_by(ContractRiskFlag.created_at.asc(), ContractRiskFlag.id.asc())
                )
            )
            contract_risk_rows.append((record, flags))
    traces = list(
        session.scalars(
            select(RuntimeControlTrace)
            .where(RuntimeControlTrace.target_record_id == deal_id)
            .order_by(RuntimeControlTrace.created_at.desc(), RuntimeControlTrace.id.desc())
        )
    )
    prompt_labels = {
        item.prompt_schema_id: item.asset_key
        for item in session.scalars(select(PromptSchemaRecord).where(PromptSchemaRecord.prompt_schema_id.in_([trace.prompt_schema_ref for trace in traces if trace.prompt_schema_ref])))
    } if traces else {}
    decisions = list(
        session.scalars(
            select(DecisionRecord).where(DecisionRecord.deal_id == deal_id).order_by(DecisionRecord.created_at.desc(), DecisionRecord.id.desc())
        )
    )
    return {
        "deal": deal,
        "summary": summary,
        "requirement_records": req_records,
        "document_requirements": doc_req_rows,
        "tech_risks": tech_risk_rows,
        "contract_risks": contract_risk_rows,
        "traces": traces,
        "prompt_labels": prompt_labels,
        "decisions": decisions,
    }


def _layout(title: str, body: str) -> str:
    return (
        "<html><head><title>"
        + html.escape(title)
        + "</title><style>body{font-family:Arial,sans-serif;max-width:960px;margin:40px auto;padding:0 16px;line-height:1.5}nav a{margin-right:12px}code{background:#f4f4f4;padding:2px 4px}</style></head><body>"
        + body
        + "</body></html>"
    )


def render_dashboard_html(session: Session) -> str:
    deals = list(session.scalars(select(Deal).where(Deal.is_deleted.is_(False)).order_by(Deal.created_at.desc(), Deal.id.desc()).limit(20)))
    rows = "".join(
        f"<li><a href='/commercial-console/deals/{html.escape(deal.deal_id)}'>{html.escape(deal.title)}</a> "
        f"({html.escape(deal.deal_id)} / {html.escape(str(deal.current_status))})</li>"
        for deal in deals
    ) or "<li>No deals available.</li>"
    return _layout(
        "Commercial Operator Dashboard",
        "<h1>Commercial Operator Dashboard</h1><p>Internal-only commercial MVP review surface.</p><ul>" + rows + "</ul>",
    )


def render_tender_card_html(session: Session, deal_id: str) -> str:
    snapshot = _load_snapshot(session, deal_id)
    deal = snapshot["deal"]
    summary = snapshot["summary"]
    nav = _deal_nav(deal_id)
    summary_text = html.escape(summary.summary_text) if summary else "No summary available."
    body = (
        nav
        + f"<h1>{html.escape(deal.title)}</h1>"
        + f"<p><strong>Deal:</strong> {html.escape(deal.deal_id)}<br>"
        + f"<strong>Customer:</strong> {html.escape(deal.customer_name or '')}<br>"
        + f"<strong>Procurement:</strong> {html.escape(deal.procurement_number or '')}<br>"
        + f"<strong>Status:</strong> {html.escape(str(deal.current_status))}</p>"
        + f"<h2>Tender Card</h2><p>{summary_text}</p>"
    )
    return _layout("Commercial Tender Card", body)


def render_report_html(session: Session, deal_id: str) -> str:
    snapshot = _load_snapshot(session, deal_id)
    nav = _deal_nav(deal_id)
    requirements = "".join(f"<li>{html.escape(row.requirement_title)}</li>" for row in snapshot["document_requirements"]) or "<li>No requirements.</li>"
    decisions = "".join(
        f"<li><code>{html.escape(item.decision_code)}</code> by {html.escape(item.decided_by_ref or 'n/a')} - {html.escape(item.rationale or '')}</li>"
        for item in snapshot["decisions"][:5]
    ) or "<li>No decisions.</li>"
    body = (
        nav
        + "<h1>Pre-Bid Report View</h1>"
        + f"<p>{html.escape(snapshot['summary'].summary_text if snapshot['summary'] else 'No summary available.')}</p>"
        + "<h2>Requirements Snapshot</h2><ul>"
        + requirements
        + "</ul><h2>Recent Decisions</h2><ul>"
        + decisions
        + "</ul>"
    )
    return _layout("Commercial Pre-Bid Report", body)


def render_requirements_html(session: Session, deal_id: str) -> str:
    snapshot = _load_snapshot(session, deal_id)
    nav = _deal_nav(deal_id)
    extracted = "".join(
        f"<li>{html.escape(item.requirement_code)}: {html.escape(item.requirement_text)}</li>"
        for item in snapshot["requirement_records"]
    ) or "<li>No extracted requirements.</li>"
    formal = "".join(
        f"<li>{html.escape(item.row_code)}: {html.escape(item.requirement_title)} "
        f"(manual_review={html.escape(str(item.requires_manual_review))})</li>"
        for item in snapshot["document_requirements"]
    ) or "<li>No formal document requirements.</li>"
    return _layout(
        "Commercial Requirements View",
        nav + "<h1>Requirements</h1><h2>Extracted</h2><ul>" + extracted + "</ul><h2>Formal</h2><ul>" + formal + "</ul>",
    )


def render_risks_html(session: Session, deal_id: str) -> str:
    snapshot = _load_snapshot(session, deal_id)
    nav = _deal_nav(deal_id)
    tech = "".join(
        f"<li>[{html.escape(str(item.severity))}] {html.escape(item.summary)}</li>"
        for item in snapshot["tech_risks"]
    ) or "<li>No technical risks.</li>"
    contract = "".join(
        f"<li>[{html.escape(str(record.severity))}] {html.escape(record.summary)}</li>"
        for record, _flags in snapshot["contract_risks"]
    ) or "<li>No contract risks.</li>"
    return _layout(
        "Commercial Risks View",
        nav + "<h1>Risks</h1><h2>Technical</h2><ul>" + tech + "</ul><h2>Contract</h2><ul>" + contract + "</ul>",
    )


def render_runtime_traces_html(session: Session, deal_id: str) -> str:
    snapshot = _load_snapshot(session, deal_id)
    nav = _deal_nav(deal_id)
    traces = "".join(
        f"<li><code>{html.escape(trace.runtime_trace_id)}</code> "
        f"{html.escape(snapshot['prompt_labels'].get(trace.prompt_schema_ref, trace.prompt_schema_ref or 'no-prompt'))} "
        f"validation={html.escape(str(trace.validation_status))} review={html.escape(str(trace.human_review_status))}</li>"
        for trace in snapshot["traces"]
    ) or "<li>No runtime traces.</li>"
    return _layout(
        "Commercial Runtime Traces",
        nav + "<h1>Runtime Trace Review</h1><ul>" + traces + "</ul>",
    )


def render_decision_html(session: Session, deal_id: str) -> str:
    snapshot = _load_snapshot(session, deal_id)
    nav = _deal_nav(deal_id)
    actions = "".join(
        f"<li><code>{html.escape(item.decision_code)}</code> - {html.escape(item.rationale or '')}</li>"
        for item in snapshot["decisions"][:10]
    ) or "<li>No recorded operator decisions.</li>"
    return _layout(
        "Commercial Decision View",
        nav
        + "<h1>Decision Action View</h1>"
        + "<p>Available actions via POST <code>/commercial-console/deals/{deal_id}/actions</code>: "
        + "<code>rejected</code>, <code>needs_more_review</code>, <code>collect_tkp</code>, <code>prepare_bid_draft</code>.</p>"
        + "<ul>"
        + actions
        + "</ul>",
    )


def _deal_nav(deal_id: str) -> str:
    return (
        "<nav>"
        f"<a href='/commercial-console'>dashboard</a>"
        f"<a href='/commercial-console/deals/{deal_id}'>tender card</a>"
        f"<a href='/commercial-console/deals/{deal_id}/report'>report</a>"
        f"<a href='/commercial-console/deals/{deal_id}/requirements'>requirements</a>"
        f"<a href='/commercial-console/deals/{deal_id}/risks'>risks</a>"
        f"<a href='/commercial-console/deals/{deal_id}/runtime-traces'>runtime traces</a>"
        f"<a href='/commercial-console/deals/{deal_id}/decision'>decision</a>"
        "</nav>"
    )


def record_operator_action(
    session: Session,
    deal_id: str,
    payload: CommercialOperatorActionRequest,
) -> CommercialOperatorActionResponse:
    _load_deal(session, deal_id)
    mapping = {
        "rejected": "OPERATOR_REJECTED_PREBID",
        "needs_more_review": "OPERATOR_MARKED_NEEDS_MORE_REVIEW",
        "collect_tkp": "OPERATOR_MARKED_COLLECT_TKP",
        "prepare_bid_draft": "OPERATOR_MARKED_PREPARE_BID_DRAFT",
    }
    decision = append_decision(
        session,
        AppendDecisionRequest(
            deal_id=deal_id,
            decision_code=mapping[payload.action],
            decided_by_type=DecisionByType.HUMAN,
            decided_by_ref=payload.operator_ref,
            rationale=payload.rationale,
            payload_json={"action": payload.action, "human_control_policy": "respected"},
        ),
    )
    event = append_event(
        session,
        AppendEventRequest(
            deal_id=deal_id,
            event_code="commercial_operator_action_recorded",
            source_module_id="C4",
            severity=EventSeverity.INFO,
            payload_json={
                "decision_id": decision.decision_id,
                "action": payload.action,
                "operator_ref": payload.operator_ref,
            },
        ),
    )
    return CommercialOperatorActionResponse(
        deal_id=deal_id,
        action=payload.action,
        decision_id=decision.decision_id,
        recorded_event_id=event.event_id,
    )
