# Calibrated Contract Risk Method

## Purpose

Define how contract risks from tender documentation are classified for tender/operator companies operating in the Russian public procurement market.

## Core Principle

Do not treat every harsh contract clause as a no-go.

The Russian public procurement market often has harsh customer contract templates, and customers rarely accept meaningful changes.

Therefore the contract memo classifies risks into three tiers:

## Tier 1: Market-Standard Harsh Term

These are common in public procurement contracts and **must not** be treated as automatic no-go.

Examples:

- Standard penalties (typically 1/300 of key rate per day)
- Post-payment after delivery/acceptance
- Strict acceptance procedures
- Unilateral termination rights for the customer
- Formal document flow requirements
- Contract security requirements

**Default treatment**: Note as market-standard. Do not flag as blocking.

## Tier 2: Commercially Material Risk

These require operator attention and may need to be factored into pricing, timeline, or supplier selection.

Examples:

- Long payment delay (60+ days after acceptance)
- High contract security (10%+ of contract value)
- Short delivery timeline (unusually compressed)
- Expensive logistics requirements
- Unclear acceptance procedure
- Required installation/commissioning
- Mismatch between delivery timeline and supplier availability
- Currency risk (pricing in one currency, payment in another)

**Default treatment**: Flag for operator review. Include in economics calculation. Not an automatic no-go but requires risk-adjusted pricing.

## Tier 3: Deal-Breaker Candidate

These may prevent participation. They require escalation before proceeding.

Examples:

- Impossible delivery timeline
- Required license/SRO/experience that the operator cannot provide
- Required certificates/declarations that cannot be obtained
- Impossible or overly narrow specifications
- Unacceptable cash gap/security requirements
- Supplier cannot meet mandatory requirements
- Unclear subject that cannot be priced safely
- Materially unbalanced contract (all risk on supplier side with no corresponding compensation)

**Default treatment**: Flag as deal-breaker candidate. Require explicit operator decision before proceeding. If the operator decides to proceed anyway, document the rationale.

## Memo Format

Each risk item in the calibrated contract risk memo includes:

- **Clause**: The specific contract clause or requirement
- **Risk description**: What the risk is
- **Classification**: market_standard_harsh_term / commercially_material_risk / deal_breaker_candidate
- **Impact assessment**: How it affects pricing, timeline, or feasibility
- **Mitigation options**: What can be done (if anything)
- **Operator decision required**: Yes/No
