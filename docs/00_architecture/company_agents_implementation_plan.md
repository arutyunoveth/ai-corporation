# Company Agents Implementation Plan

## Files to change

### Enums
- `src/shared/enums/mvp_phase1.py` — add AgentScope, AgentKind, CompanyAgentActivationState, DataPolicy, RuntimeMode, ModelTier enums
- `src/shared/enums/__init__.py` — export new enums

### Models
- `src/modules/agent_registry/models.py` — add columns to AgentRegistryRecord: agent_scope, agent_kind, reports_to, data_policy, runtime_mode, model_tier, description, responsibilities (JSON), inputs (JSON), outputs (JSON), escalation_rules (JSON), forbidden_actions (JSON)

### Schemas
- `src/modules/agent_registry/schemas.py` — extend BuildAgentRegistryEntryInput and AgentRegistryRecordResponse with new fields

### Service
- `src/modules/agent_registry/service.py` — resolve new fields in build flow

### Company agent seeds
- `src/modules/agent_registry/company_agents.py` — new file: seed data for 7 active + 13 inactive company agents, function to build company agent registry set

### Context assets
- `docs/agents/company/A00_chief_of_staff/identity.md`
- `docs/agents/company/A00_chief_of_staff/soul.md`
- `docs/agents/company/A00_chief_of_staff/agent.md`
- `docs/agents/company/A10_tender_operator/identity.md`
- `docs/agents/company/A10_tender_operator/soul.md`
- `docs/agents/company/A10_tender_operator/agent.md`
- `docs/agents/company/A11_rfq_supplier_analyst/identity.md`
- `docs/agents/company/A11_rfq_supplier_analyst/soul.md`
- `docs/agents/company/A11_rfq_supplier_analyst/agent.md`
- `docs/agents/company/A20_finance_unit_economics/identity.md`
- `docs/agents/company/A20_finance_unit_economics/soul.md`
- `docs/agents/company/A20_finance_unit_economics/agent.md`
- `docs/agents/company/A21_legal_contract_risk/identity.md`
- `docs/agents/company/A21_legal_contract_risk/soul.md`
- `docs/agents/company/A21_legal_contract_risk/agent.md`
- `docs/agents/company/A40_cto_system_architect/identity.md`
- `docs/agents/company/A40_cto_system_architect/soul.md`
- `docs/agents/company/A40_cto_system_architect/agent.md`
- `docs/agents/company/A42_qa_release/identity.md`
- `docs/agents/company/A42_qa_release/soul.md`
- `docs/agents/company/A42_qa_release/agent.md`

### Exporter
- `scripts/export_company_agent_context.py` — CLI script to export agent context from local files

### Policy
- `docs/agents/company/Company_Agent_Runtime_Policy.md`

### Workflow routes
- `src/modules/workflow_runs/company_workflow_routes.py` — company workflow route metadata (no runtime execution)

### Artifact templates
- `docs/agents/company/templates/` — CEO Decision Memo, Finance Memo, Contract Risk Memo, RFQ Draft, Supplier Comparison Memo, QA Readiness Memo, Inter-Agent Handoff, Escalation Note

### Governance docs
- `docs/00_architecture/company_agents_metadata_extension.md`
- `docs/00_architecture/company_agents_implementation_plan.md`

### Tests
- `tests/company_agents/__init__.py`
- `tests/company_agents/test_company_agent_registry_scope.py`
- `tests/company_agents/test_company_agent_prompt_assets.py`
- `tests/company_agents/test_company_agent_context_export.py`
- `tests/company_agents/test_company_agent_runtime_policy.py`
- `tests/company_agents/test_company_workflow_routes.py`

## Enum values

```python
class AgentScope(StrEnum):
    PRODUCT = "product"
    COMPANY_OPERATIONS = "company_operations"
    PLATFORM = "platform"

class AgentKind(StrEnum):
    OPERATING_SYSTEM = "operating_system"
    TENDER_OPERATIONS = "tender_operations"
    RISK_FINANCE_LEGAL = "risk_finance_legal"
    ENGINEERING = "engineering"
    GROWTH = "growth"
    DELIVERY = "delivery"
    RESEARCH = "research"

class CompanyAgentActivationState(StrEnum):
    DRAFT = "draft"
    ACTIVE_METADATA_ONLY = "active_metadata_only"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"

class DataPolicy(StrEnum):
    LOCAL_ONLY = "local_only"
    LOCAL_FIRST = "local_first"
    HYBRID_PUBLIC_ONLY = "hybrid_public_only"

class RuntimeMode(StrEnum):
    METADATA_ONLY = "metadata_only"
    MANUAL_CONTEXT_ONLY = "manual_context_only"
    DEFERRED_EXECUTION = "deferred_execution"

class ModelTier(StrEnum):
    REASONING = "reasoning"
    STANDARD = "standard"
    CODE_REASONING = "code_reasoning"
    WRITING = "writing"
```

## How agent_scope integrates with existing model

The existing `AgentRegistryRecord` has:
- `activation_state` (AgentActivationState: REVIEWED/ENABLED/DISABLED)
- `registry_scope` on AgentRegistrySet level

New approach:
- Add `agent_scope` column to AgentRegistryRecord (product/company_operations/platform)
- Add `agent_kind`, `reports_to`, `data_policy`, `runtime_mode`, `model_tier` columns
- Add JSON columns for `responsibilities`, `inputs`, `outputs`, `escalation_rules`, `forbidden_actions`
- Company agents use CompanyAgentActivationState values stored in `activation_state` field (extended enum)
- The `notes` field can store the `description`

## Boundaries preserved

- No new canonical module
- No prompt execution runtime
- No autonomous orchestration
- No cloud dispatch
- All company agents: runtime_mode = manual_context_only or metadata_only
- All company agents: execution_allowed = false
