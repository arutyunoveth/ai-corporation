# M-049 / M-050 Contracts And Interfaces Draft

## Design Intent

These contracts are design-level only. They describe future interface boundaries without creating runtime endpoints, models, or execution behavior.

## M-049 Agent Registry Contracts

### Registry Definition Contract

- `registry_scope`
- `agent_key`
- `agent_label`
- `owner_role`
- `reviewer_role`
- `activation_state`
- `allowed_capabilities`
- `blocked_capabilities`
- `linked_prompt_assets`
- `approval_reference`

### Registry Policy Interface

Expected future interface responsibilities:

- list reviewed agent definitions
- resolve a single agent definition by approved key
- expose activation state
- expose safety policy and ownership metadata

Not authorized in this phase:

- runtime execution
- model binding
- external tool invocation

## M-050 Prompt / Schema Library Contracts

### Prompt Asset Contract

- `asset_key`
- `asset_type`
- `version_tag`
- `owner_role`
- `reviewer_role`
- `usage_constraints`
- `input_schema_ref`
- `output_schema_ref`
- `safety_notes`
- `status`

### Library Resolution Interface

Expected future interface responsibilities:

- resolve approved prompt/schema assets by key and version
- expose declared constraints and schema references
- expose approval lineage

Not authorized in this phase:

- prompt execution
- automatic prompt selection
- implicit live model coupling

## Cross-Module Dependency Contracts

- `M-049` may depend on `M-050` for reviewed asset references
- `M-049/M-050` may later depend on supporting controls from `M-052..M-055`
- any future activation must preserve governance mapping for reserved slots

## Plan Alignment

- Master Plan matched: `yes`
- What changed vs plan: `contracts are design-level drafts only`
- Any drift introduced: `no`
