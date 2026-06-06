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
