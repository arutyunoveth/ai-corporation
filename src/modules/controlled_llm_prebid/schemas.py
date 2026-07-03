from pydantic import BaseModel, Field


class LLMTenderSummaryDraft(BaseModel):
    tender_summary: str = Field(min_length=1)
    why_relevant: str = Field(min_length=1)


class LLMTechnicalRequirementsDraft(BaseModel):
    technical_requirements: list[str] = Field(min_length=1)


class LLMParticipantRequirementsDraft(BaseModel):
    participant_requirements: list[str] = Field(min_length=1)


class LLMContractRisksDraft(BaseModel):
    contract_risks: list[str] = Field(min_length=1)


class LLMBidDecisionDraft(BaseModel):
    recommendation: str = Field(pattern="^(GO|GO_WITH_CONDITIONS|NEEDS_REVIEW|NO_GO)$")
    rationale: str = Field(min_length=1)
    next_actions: list[str] = Field(min_length=1)


class LLMTenderOperatorRequirementsDraft(BaseModel):
    tender_summary: str = Field(min_length=1)
    technical_requirements: list[str] = Field(min_length=1)
    qualification_requirements: list[str] = Field(min_length=1)
    document_requirements: list[str] = Field(min_length=1)
    evaluation_criteria: list[str] = Field(min_length=1)
    procurement_categories: list[str] = Field(min_length=1)


class LLMSupplierQuestionDraft(BaseModel):
    question: str = Field(min_length=1)
    category: str = Field(min_length=1)


class LLMSupplierQuestionsDraft(BaseModel):
    supplier_questions: list[LLMSupplierQuestionDraft] = Field(min_length=1)


class LLMTenderOperatorRFQDraft(BaseModel):
    email_subject: str = Field(min_length=1)
    intro: str = Field(min_length=1)
    requirements_summary: list[str] = Field(min_length=1)
    supplier_questions: list[str] = Field(min_length=1)
    requested_response_items: list[str] = Field(min_length=1)
    commercial_terms: list[str] = Field(min_length=1)
    closing_note: str = Field(min_length=1)


class LLMContractRiskItemDraft(BaseModel):
    clause: str = Field(min_length=1)
    description: str = Field(min_length=1)
    classification: str = Field(
        pattern="^(market_standard_harsh_term|commercially_material_risk|deal_breaker_candidate)$"
    )
    impact: str = Field(min_length=1)
    mitigation: str = Field(min_length=1)
    operator_decision_required: bool


class LLMTenderOperatorContractRiskMemoDraft(BaseModel):
    contract_risks: list[LLMContractRiskItemDraft] = Field(min_length=1)


class LLMNormalizedQuoteDraft(BaseModel):
    supplier_label: str = Field(min_length=1)
    price_per_unit: str = Field(min_length=1)
    price_total: str = Field(min_length=1)
    currency: str = Field(min_length=1)
    price_with_vat: str = Field(min_length=1)
    price_without_vat: str = Field(min_length=1)
    delivery_cost: str = Field(min_length=1)
    delivery_time_days: str = Field(min_length=1)
    warranty_months: str = Field(min_length=1)
    payment_terms: str = Field(min_length=1)
    offer_validity_days: str = Field(min_length=1)
    has_certificates: str = Field(min_length=1)
    installation_included: str = Field(min_length=1)
    notes: str = Field(min_length=1)
    status: str = Field(pattern="^(normalized|needs_operator_review)$")


class LLMQuoteNormalizationDraft(BaseModel):
    suppliers: list[LLMNormalizedQuoteDraft] = Field(min_length=1)


class LLMTenderOperatorBidDecisionDraft(BaseModel):
    preliminary_recommendation: str = Field(pattern="^(GO|GO_WITH_CONDITIONS|NEEDS_REVIEW|NO_GO)$")
    rationale: str = Field(min_length=1)
    next_actions: list[str] = Field(min_length=1)
    human_review_required: bool = True
