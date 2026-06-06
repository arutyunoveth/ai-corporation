from datetime import datetime
from typing import Literal

from pydantic import Field

from src.shared.enums import ApprovalDecision
from src.shared.types.common import APIModel


class BuildCommercialSupplierRequestDraftRequest(APIModel):
    operator_ref: str | None = None
    notes: str | None = None


class ManualSupplierQuoteInput(APIModel):
    legal_name: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    inn: str = Field(min_length=1)
    country_code: str = Field(default="RU", min_length=2)
    contact_name: str = Field(min_length=1)
    contact_email: str | None = None
    contact_phone: str | None = None
    tags: list[str] = Field(default_factory=list)
    quoted_amount: float = Field(gt=0)
    currency_code: str = Field(default="RUB", min_length=3)
    notes: str | None = None


class RegisterCommercialTKPBatchRequest(APIModel):
    operator_ref: str = Field(min_length=1)
    suppliers: list[ManualSupplierQuoteInput] = Field(min_length=1)


class BuildCommercialBidReadinessRequest(APIModel):
    operator_ref: str = Field(min_length=1)


class CommercialBidWorkspaceActionRequest(APIModel):
    action: Literal["tkp_needed", "tkp_received", "economics_reviewed", "ready_for_human_submission"]
    operator_ref: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    approval_decision: ApprovalDecision | None = None
    conditions: list[str] = Field(default_factory=list)


class CommercialSupplierRequestDraftResponse(APIModel):
    deal_id: str
    generated_at: datetime
    request_subject: str
    request_body: str
    supplier_questions: list[str]
    based_on: dict


class CommercialManualTKPBatchResponse(APIModel):
    deal_id: str
    supplier_ids: list[str]
    quote_ids: list[str]
    supplier_shortlist_id: str
    rfq_batch_id: str
    supplier_communication_set_id: str
    quote_set_id: str
    registered_at: datetime


class CommercialWorkspaceSnapshotResponse(APIModel):
    deal_id: str
    generated_at: datetime
    latest_ids: dict
    supplier_request_draft: dict
    tkp_summary: dict
    economics_summary: dict
    readiness_summary: dict
    executive_report_markdown: str
    executive_report_json: dict


class CommercialBidWorkspaceActionResponse(APIModel):
    deal_id: str
    action: str
    decision_id: str
    recorded_event_id: str
    submission_readiness_set_id: str | None = None
    submission_readiness_status: str | None = None
