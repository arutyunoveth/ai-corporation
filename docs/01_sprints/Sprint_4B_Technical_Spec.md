# Sprint 4B Technical Spec
## Modules M-026, M-027, M-028

## Purpose
Sprint 4B builds the risk and approval layer on top of the existing foundation, analysis, supplier-quality, and economics contours.

Modules:
- `M-026` Contract Risk Parser
- `M-027` Integrated Risk Memo Builder
- `M-028` CEO Approval Cockpit

## Result
By the end of Sprint 4B the system must:
1. build persisted contract risks from formal document context;
2. aggregate technical, supplier, quote, finance, and contract risks into one persisted memo;
3. build a formal approval package;
4. persist explicit human decision append-only;
5. keep recommendation and human decision separate;
6. emit event and audit trace.

Output:
`contract risks + integrated risk memo + CEO approval`

## Out Of Scope
- bid prep
- submission
- execution
- full legal NLP
- external workflow orchestration

## Dependencies
- deal, event log, decision journal, document store
- initial tech risks
- supplier verification and quote comparison
- finance memo
- persisted tender documents

## Architecture Principles
1. Contract risk is persisted, not transient.
2. Integrated risk memo aggregates source layers and does not replace them.
3. Approval is a formal business object.
4. Human decisions remain append-only.
5. System recommendation and final human decision remain separate.
