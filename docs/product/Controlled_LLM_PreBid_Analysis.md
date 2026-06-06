# Controlled LLM Pre-Bid Analysis

## Goal

Use bounded `M-049/M-050` metadata plus the runtime trace ledger to add controlled LLM-assisted pre-bid analysis on top of the deterministic commercial demo flow.

## Supported Modes

- `provider=deterministic`
- `provider=stub`
- `provider=llm`

## Control Rules

- every LLM-backed section is linked to prompt/schema metadata
- every LLM-backed section creates a runtime trace
- every output is validated against a structured schema
- every output remains marked for human review
- invalid output does not auto-advance anything and remains `needs_manual_review`

## Explicit Boundaries

- no autonomous bid submission
- no supplier email automation
- no procurement-platform execution
- no automatic final legal/commercial decision
- no broad agent runtime opening
