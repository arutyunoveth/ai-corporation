# M-049 / M-050 Limited Runtime Design

## Scope

This document defines the limited runtime **design** posture for:

- `M-049 Agent Registry`
- `M-050 Prompt / Schema Library`

It does **not** authorize runtime implementation.

## Target Design Role

### M-049 Agent Registry

Target role:

- maintain a controlled catalog of allowed agent definitions
- bind each agent concept to governance, ownership, and activation policy
- prevent ad hoc runtime proliferation

Design-only interpretation:

- registry contracts are defined
- activation remains closed
- no runtime execution path is added in this phase

### M-050 Prompt / Schema Library

Target role:

- maintain approved prompt/specification assets
- bind prompt assets to versioning, safety review, and compatibility expectations
- support future runtime consumers through reviewed contracts rather than direct execution

Design-only interpretation:

- library structure is defined
- prompt execution remains closed
- no runtime resolution layer is added in this phase

## Intended Interaction Between M-049 And M-050

`M-049` governs which agent definitions may exist.
`M-050` governs which prompt/schema assets those agent definitions may reference.

Future implementation may only open after:

1. agent-policy boundaries are approved
2. prompt/schema safety boundaries are approved
3. a separate implementation phase is explicitly authorized

## Design Checkpoint Entry

- owner: `Limited Runtime Design Owner`
- reviewer: `Limited Runtime Design Reviewer`
- proceed / pause / stop: `proceed`
- rationale: design scope is explicit enough to prepare bounded contracts without implying runtime opening

## Plan Alignment

- Master Plan matched: `yes`
- What changed vs plan: `only repo-local design artifacts were added`
- Any drift introduced: `no`
