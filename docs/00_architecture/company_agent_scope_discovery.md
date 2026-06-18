# Company Agent Scope Discovery

## Existing M-049 files found

| File | Purpose |
|------|---------|
| `src/modules/agent_registry/models.py` | SQLAlchemy models: AgentRegistrySet, AgentRegistryRecord |
| `src/modules/agent_registry/schemas.py` | Pydantic schemas: BuildAgentRegistryEntryInput, BuildAgentRegistryRequest, responses |
| `src/modules/agent_registry/service.py` | Business logic: build_agent_registry, get/set/list operations |
| `src/modules/agent_registry/router.py` | FastAPI router: POST build, GET by id, GET list, GET records |
| `src/shared/enums/mvp_phase1.py` | AgentActivationState, AgentRegistryStatus, AgentLifecycleStatus |
| `src/shared/ids/generators.py` | next_agent_registry_set_id (ARS), next_agent_registry_id (AR) |
| `tests/test_mvp_runtime_phase_1_m049_runtime.py` | M-049 build and persist tests |

## Existing M-050 files found

| File | Purpose |
|------|---------|
| `src/modules/prompt_schema_library/models.py` | SQLAlchemy models: PromptSchemaLibrarySet, PromptSchemaRecord, AgentPromptLink |
| `src/modules/prompt_schema_library/schemas.py` | Pydantic schemas: BuildPromptSchemaAssetInput, BuildPromptSchemaLibraryRequest, responses |
| `src/modules/prompt_schema_library/service.py` | Business logic: build_prompt_schema_library, get/set/list operations |
| `src/modules/prompt_schema_library/router.py` | FastAPI router: POST build, GET by id, GET list, GET records |
| `src/shared/enums/mvp_phase1.py` | PromptSchemaAssetType, PromptSchemaAssetStatus, PromptValidationMode, PromptRiskClass |
| `src/shared/ids/generators.py` | next_prompt_schema_library_set_id (PSLS), next_prompt_schema_id (PS) |
| `tests/test_mvp_runtime_phase_1_m050_runtime.py` | M-050 build and link tests |

## Existing M-051 files found

| File | Purpose |
|------|---------|
| `src/modules/workflow_runs/models.py` | SQLAlchemy models: WorkflowRunSet, WorkflowRunRecord, WorkflowStepRecord |
| `src/modules/workflow_runs/schemas.py` | Pydantic schemas: BuildWorkflowRunRequest, responses |
| `src/modules/workflow_runs/service.py` | Business logic: build_workflow_run (4 workflow builders), get/set/list |
| `src/modules/workflow_runs/router.py` | FastAPI router: POST build, GET by id, GET list, GET records |
| `src/shared/enums/sprint7b.py` | WorkflowScopeType, WorkflowStatus, WorkflowStepType, WorkflowStepStatus |
| `src/shared/ids/generators.py` | next_workflow_run_set_id (WRS), next_workflow_run_id (WR), next_workflow_step_id (WS) |
| `tests/test_sprint7b_integration.py` | M-051 workflow build and step tests |

## Existing enums / models / services / routers

- AgentActivationState: REVIEWED, ENABLED, DISABLED
- AgentRegistryStatus: BUILT, FAILED
- AgentLifecycleStatus: REVIEWED, ENABLED, DISABLED
- PromptSchemaAssetType: PROMPT_TEMPLATE, INPUT_SCHEMA, OUTPUT_SCHEMA, COMPOSITE
- PromptSchemaAssetStatus: REVIEWED, ENABLED, DISABLED
- WorkflowScopeType: DEAL, PIPELINE, EXECUTION, PORTFOLIO
- WorkflowStatus: BUILT, ACTIVE, COMPLETED, FAILED, STALE

## Recommended extension point

1. Add new enums to `src/shared/enums/mvp_phase1.py`: AgentScope, AgentKind, CompanyAgentActivationState, DataPolicy, RuntimeMode, ModelTier
2. Add new columns to `AgentRegistryRecord`: agent_scope, agent_kind, reports_to, data_policy, runtime_mode, model_tier, description, responsibilities, inputs, outputs, escalation_rules, forbidden_actions
3. Add company agent seed data as a service function in `src/modules/agent_registry/company_agents.py`
4. Add context asset files under `docs/agents/company/`
5. Add exporter script `scripts/export_company_agent_context.py`
6. Add company workflow route metadata as a service function in `src/modules/workflow_runs/company_workflow_routes.py`

## Duplication risks

- The existing `activation_state` field uses AgentActivationState (REVIEWED/ENABLED/DISABLED). Company agents need different states (draft/active_metadata_only/inactive/deprecated). Solution: add a new CompanyAgentActivationState enum and use it via the notes or a new field, OR extend AgentActivationState. Best approach: add company-specific activation states to AgentActivationState enum since they are additive.
- The existing `registry_scope` field on AgentRegistrySet is a free-text field. Company agents will use `agent_scope` on individual records, not on the set. This avoids changing the set-level scope.

## Confirmed boundaries

This change must remain metadata/control only.
No prompt execution runtime is opened.
No autonomous agent execution is opened.
No cloud dispatch is introduced.
No new canonical module is created.
