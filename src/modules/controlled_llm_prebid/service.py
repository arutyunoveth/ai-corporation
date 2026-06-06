import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.agent_registry.models import AgentRegistryRecord
from src.modules.agent_registry.schemas import BuildAgentRegistryEntryInput, BuildAgentRegistryRequest
from src.modules.agent_registry.service import build_agent_registry
from src.modules.controlled_llm_prebid.schemas import (
    LLMBidDecisionDraft,
    LLMContractRisksDraft,
    LLMParticipantRequirementsDraft,
    LLMTechnicalRequirementsDraft,
    LLMTenderSummaryDraft,
)
from src.modules.prompt_schema_library.models import PromptSchemaRecord
from src.modules.prompt_schema_library.schemas import BuildPromptSchemaAssetInput, BuildPromptSchemaLibraryRequest
from src.modules.prompt_schema_library.service import build_prompt_schema_library
from src.modules.runtime_control_traces.schemas import CreateRuntimeControlTraceRequest
from src.modules.runtime_control_traces.service import create_runtime_control_trace
from src.shared.config.settings import get_settings
from src.shared.enums import (
    AgentActivationState,
    HumanReviewStatus,
    PromptRiskClass,
    PromptSchemaAssetStatus,
    PromptSchemaAssetType,
    PromptValidationMode,
    RuntimeTraceActionType,
    RuntimeTraceActorType,
    RuntimeTraceDisposition,
    RuntimeTraceValidationStatus,
)
from src.shared.errors import ValidationError


AGENT_KEY = "commercial-prebid-analyst"
PROMPT_VERSION = "v1"
RUNTIME_CONTEXT = "COMMERCIAL_PREBID_ANALYSIS"


class _PromptSpec:
    def __init__(self, asset_key: str, purpose: str, output_schema_ref: str, template: str) -> None:
        self.asset_key = asset_key
        self.purpose = purpose
        self.output_schema_ref = output_schema_ref
        self.template = template


PROMPT_SPECS = {
    "tender_summary": _PromptSpec(
        asset_key="commercial-prebid-tender-summary",
        purpose="Generate a bounded summary and relevance statement for internal pre-bid analysis.",
        output_schema_ref="LLMTenderSummaryDraft",
        template=(
            "Summarize the tender for an internal operator. "
            "Return JSON with keys tender_summary and why_relevant."
        ),
    ),
    "technical_requirements": _PromptSpec(
        asset_key="commercial-prebid-technical-requirements",
        purpose="Extract a bounded list of technical requirements for internal review.",
        output_schema_ref="LLMTechnicalRequirementsDraft",
        template="Return JSON with key technical_requirements as a list of strings.",
    ),
    "participant_requirements": _PromptSpec(
        asset_key="commercial-prebid-participant-requirements",
        purpose="Extract bidder or participant requirements for internal review.",
        output_schema_ref="LLMParticipantRequirementsDraft",
        template="Return JSON with key participant_requirements as a list of strings.",
    ),
    "contract_risks": _PromptSpec(
        asset_key="commercial-prebid-contract-risks",
        purpose="Highlight contract-risk themes without making final legal decisions.",
        output_schema_ref="LLMContractRisksDraft",
        template="Return JSON with key contract_risks as a list of strings.",
    ),
    "bid_decision": _PromptSpec(
        asset_key="commercial-prebid-bid-decision",
        purpose="Draft a bounded recommendation for internal review only.",
        output_schema_ref="LLMBidDecisionDraft",
        template=(
            "Return JSON with keys recommendation, rationale, and next_actions. "
            "Recommendation must be GO, GO_WITH_CONDITIONS, NEEDS_REVIEW, or NO_GO."
        ),
    ),
}

OUTPUT_MODELS = {
    "tender_summary": LLMTenderSummaryDraft,
    "technical_requirements": LLMTechnicalRequirementsDraft,
    "participant_requirements": LLMParticipantRequirementsDraft,
    "contract_risks": LLMContractRisksDraft,
    "bid_decision": LLMBidDecisionDraft,
}


@dataclass
class ControlledLLMAnalysisResult:
    analysis_mode: str
    overall_review_status: str
    sections: dict[str, dict[str, Any]]
    trace_ids: list[str]


def _find_agent(session: Session) -> AgentRegistryRecord | None:
    return session.scalar(select(AgentRegistryRecord).where(AgentRegistryRecord.agent_key == AGENT_KEY))


def _find_prompt(session: Session, asset_key: str) -> PromptSchemaRecord | None:
    return session.scalar(
        select(PromptSchemaRecord).where(
            PromptSchemaRecord.asset_key == asset_key,
            PromptSchemaRecord.version_tag == PROMPT_VERSION,
        )
    )


def _ensure_metadata(session: Session) -> tuple[AgentRegistryRecord, dict[str, PromptSchemaRecord]]:
    agent = _find_agent(session)
    if agent is None:
        registry_set = build_agent_registry(
            session,
            BuildAgentRegistryRequest(
                registry_scope="INTERNAL",
                entries=[
                    BuildAgentRegistryEntryInput(
                        agent_key=AGENT_KEY,
                        agent_label="Commercial Pre-Bid Analyst",
                        owner_operator="Runtime Owner",
                        reviewer_role="Commercial Reviewer",
                        activation_state=AgentActivationState.REVIEWED,
                        allowed_action_classes=["DRAFT_ANALYSIS", "STRUCTURE_METADATA"],
                        forbidden_action_classes=[
                            "AUTONOMOUS_SUBMISSION",
                            "SUPPLIER_OUTREACH",
                            "EXTERNAL_EXECUTION",
                        ],
                        description="Bounded commercial pre-bid drafting profile with mandatory human review.",
                    )
                ],
            ),
        )
        agent_records = session.scalars(
            select(AgentRegistryRecord).where(AgentRegistryRecord.agent_registry_set_id == registry_set.agent_registry_set_id)
        ).all()
        agent = list(agent_records)[0]

    prompts: dict[str, PromptSchemaRecord] = {}
    missing_sections: list[str] = []
    for section, spec in PROMPT_SPECS.items():
        prompt = _find_prompt(session, spec.asset_key)
        if prompt is None:
            missing_sections.append(section)
        else:
            prompts[section] = prompt

    if missing_sections:
        assets: list[BuildPromptSchemaAssetInput] = []
        for section in missing_sections:
            spec = PROMPT_SPECS[section]
            output_schema = OUTPUT_MODELS[section].model_json_schema()
            assets.append(
                BuildPromptSchemaAssetInput(
                    asset_key=spec.asset_key,
                    prompt_name=spec.asset_key,
                    asset_type=PromptSchemaAssetType.PROMPT_TEMPLATE,
                    prompt_version=PROMPT_VERSION,
                    owner_operator="Runtime Owner",
                    reviewer_role="Commercial Reviewer",
                    asset_status=PromptSchemaAssetStatus.REVIEWED,
                    prompt_purpose=spec.purpose,
                    associated_runtime_slice="COMMERCIAL_MVP_V1",
                    input_schema_ref="COMMERCIAL_PREBID_CONTEXT_V1",
                    output_schema_ref=spec.output_schema_ref,
                    validation_mode=PromptValidationMode.STRICT,
                    allowed_use_contexts=[RUNTIME_CONTEXT],
                    forbidden_use_contexts=[
                        "AUTONOMOUS_SUBMISSION",
                        "SUPPLIER_OUTREACH",
                        "LEGAL_FINAL_DECISION",
                        "PROCUREMENT_PLATFORM_EXECUTION",
                    ],
                    human_review_required=True,
                    risk_class=PromptRiskClass.HIGH,
                    notes="Controlled LLM commercial pre-bid analysis only.",
                    rationale="Bounded draft-generation only; all outputs require human review.",
                    asset_payload_json={
                        "template": spec.template,
                        "output_schema_json": output_schema,
                    },
                    linked_agent_registry_ids=[agent.agent_registry_id],
                )
            )
        build_prompt_schema_library(
            session,
            BuildPromptSchemaLibraryRequest(library_scope="INTERNAL", assets=assets),
        )
        for section, spec in PROMPT_SPECS.items():
            prompts[section] = _find_prompt(session, spec.asset_key)  # type: ignore[assignment]

    return agent, prompts


class _StubProvider:
    def __init__(self, invalid: bool = False) -> None:
        self.invalid = invalid

    def generate(self, section: str, context: dict[str, Any]) -> dict[str, Any]:
        if self.invalid and section == "bid_decision":
            return {"recommendation": "AUTO_SUBMIT"}
        if section == "tender_summary":
            return {
                "tender_summary": f"{context['title']} for {context['customer_name']} with a staged delivery scope.",
                "why_relevant": "Matches the company's electrical-supply profile and supports a bounded pre-bid review.",
            }
        if section == "technical_requirements":
            return {
                "technical_requirements": [
                    "Provide low-voltage switchgear cabinets.",
                    "Support staged delivery and commissioning-ready labeling.",
                    "Include warranty and technical-passport package.",
                ]
            }
        if section == "participant_requirements":
            return {
                "participant_requirements": context["participant_requirements"],
            }
        if section == "contract_risks":
            return {
                "contract_risks": [
                    "Payment timing must be reviewed manually.",
                    "Delay penalties should be reconciled with delivery assumptions.",
                    "Acceptance flow must be clarified before bid drafting.",
                ]
            }
        if section == "bid_decision":
            return {
                "recommendation": "GO_WITH_CONDITIONS",
                "rationale": "Technically relevant, but contract/payment assumptions still require manual review.",
                "next_actions": [
                    "Confirm contract payment terms.",
                    "Validate acceptance package and staged delivery assumptions.",
                ],
            }
        raise ValidationError(f"Unsupported stub analysis section '{section}'")


class _OpenAICompatibleProvider:
    def __init__(self) -> None:
        self.settings = get_settings()

    def generate(self, section: str, context: dict[str, Any], prompt_record: PromptSchemaRecord) -> dict[str, Any]:
        if not self.settings.openai_api_key:
            raise ValidationError("AI_CORP_OPENAI_API_KEY is required for provider='llm'")
        model = self.settings.llm_model or "gpt-4.1-mini"
        prompt_template = prompt_record.asset_payload_json.get("template", "")
        body = {
            "model": model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a controlled internal commercial analysis assistant. "
                        "Return valid JSON only. Do not suggest external execution."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "task": section,
                            "prompt_template": prompt_template,
                            "context": context,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }
        request = Request(
            url=f"{self.settings.openai_base_url.rstrip('/')}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.openai_api_key}",
            },
            method="POST",
        )
        last_error: Exception | None = None
        for _attempt in range(max(self.settings.llm_max_retries, 1)):
            try:
                with urlopen(request, timeout=self.settings.llm_timeout_seconds) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    content = payload["choices"][0]["message"]["content"]
                    if not isinstance(content, str):
                        raise ValidationError("OpenAI-compatible provider did not return string content")
                    return json.loads(content)
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, KeyError, ValidationError) as exc:
                last_error = exc
        raise ValidationError(f"LLM provider call failed: {last_error}")


def _validate_output(section: str, raw_output: dict[str, Any]) -> dict[str, Any]:
    model = OUTPUT_MODELS[section]
    validated = model.model_validate(raw_output)
    return validated.model_dump()


def run_controlled_llm_prebid_analysis(
    session: Session,
    *,
    provider_mode: str,
    context: dict[str, Any],
    simulate_invalid_output: bool = False,
) -> ControlledLLMAnalysisResult:
    agent, prompt_records = _ensure_metadata(session)

    if provider_mode == "stub":
        provider = _StubProvider(invalid=simulate_invalid_output)
        analysis_mode = "llm_controlled_stub"
    elif provider_mode == "llm":
        provider = _OpenAICompatibleProvider()
        analysis_mode = "llm_controlled_provider"
    else:
        raise ValidationError(f"Unsupported provider_mode '{provider_mode}'")

    sections: dict[str, dict[str, Any]] = {}
    trace_ids: list[str] = []
    overall_review_status = HumanReviewStatus.NEEDS_HUMAN_REVIEW.value

    for section, prompt_record in prompt_records.items():
        try:
            if provider_mode == "stub":
                raw_output = provider.generate(section, context)
            else:
                raw_output = provider.generate(section, context, prompt_record)
            validated_output = _validate_output(section, raw_output)
            validation_status = RuntimeTraceValidationStatus.PASSED
            review_status = HumanReviewStatus.NEEDS_HUMAN_REVIEW
            disposition = RuntimeTraceDisposition.NEEDS_HUMAN_REVIEW
        except Exception as exc:
            raw_output = {"error": str(exc)}
            validated_output = None
            validation_status = RuntimeTraceValidationStatus.FAILED
            review_status = HumanReviewStatus.VALIDATION_FAILED
            disposition = RuntimeTraceDisposition.NEEDS_HUMAN_REVIEW
            overall_review_status = HumanReviewStatus.NEEDS_HUMAN_REVIEW.value

        trace = create_runtime_control_trace(
            session,
            CreateRuntimeControlTraceRequest(
                runtime_slice="COMMERCIAL_MVP_V1",
                source_entity="COMMERCIAL_PREBID_LLM_ANALYSIS",
                actor_type=RuntimeTraceActorType.AGENT_PROFILE,
                actor_ref=agent.agent_key,
                action_type=RuntimeTraceActionType.GENERATE_DRAFT,
                target_module="commercial_prebid_demo",
                target_record_id=context["deal_id"],
                prompt_schema_ref=prompt_record.prompt_schema_id,
                agent_profile_ref=agent.agent_registry_id,
                input_summary=f"Controlled commercial pre-bid analysis for section '{section}'",
                output_summary=json.dumps(raw_output, ensure_ascii=False)[:500],
                validation_status=validation_status,
                human_review_status=review_status,
                final_disposition=disposition,
            ),
        )
        trace_ids.append(trace.runtime_trace_id)
        sections[section] = {
            "prompt_schema_id": prompt_record.prompt_schema_id,
            "prompt_version": prompt_record.version_tag,
            "output_schema_ref": prompt_record.output_schema_ref,
            "validation_status": validation_status.value,
            "review_status": review_status.value,
            "requires_human_review": True,
            "trace_id": trace.runtime_trace_id,
            "raw_output": raw_output,
            "validated_output": validated_output,
        }

    if any(item["validation_status"] == RuntimeTraceValidationStatus.FAILED.value for item in sections.values()):
        overall_review_status = HumanReviewStatus.NEEDS_HUMAN_REVIEW.value

    return ControlledLLMAnalysisResult(
        analysis_mode=analysis_mode,
        overall_review_status=overall_review_status,
        sections=sections,
        trace_ids=trace_ids,
    )
