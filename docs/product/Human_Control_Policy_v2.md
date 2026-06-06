# Human Control Policy v2

## Principle

All commercial MVP outputs are advisory or preparatory unless a human operator explicitly reviews and advances the workflow.

## Required Controls

- operator review for commercial recommendations
- schema validation for any structured LLM-assisted output
- runtime trace or event logging for key metadata/control actions
- explicit status markers for `needs_manual_review` or equivalent bounded review states
- no automatic external execution

## Prohibited Behavior

- no autonomous supplier outreach
- no autonomous tender submission
- no automatic acceptance of legal/commercial recommendations
- no self-triggered execution loops

## Review Standard

Any future LLM-backed artifact must expose:

- provider or stub source
- prompt/schema reference
- validation result
- human review requirement
- final operator disposition
