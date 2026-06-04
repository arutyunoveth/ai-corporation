# Canonical Module Registry Locked

## Purpose

This document locks the canonical business-module registry for the repository.

From this reconciliation step forward, the only valid top-level canonical business modules are:

- `M-001` through `M-055`

Anything useful that exists outside this registry must be treated as:

- helper
- submodule
- platform service
- adapter
- support contour
- internal extension

and not as a new canonical business module.

## Hard Rule

1. New top-level business modules may be created only if they already exist in the master registry.
2. No new canonical IDs may be introduced outside `M-001..M-055`.
3. Existing drift modules do not become canonical just because they are implemented in code.
4. If a useful capability is missing from the registry, it must first be reconciled into the registry at the governance level before receiving a canonical top-level identity.

## Locked Canonical List

| Canonical ID | Locked canonical module |
|---|---|
| M-001 | Deal Card Core |
| M-002 | Deal Status Model |
| M-003 | Document Store |
| M-004 | Event Log & Decision Journal |
| M-005 | Counterparty / Customer Registry |
| M-006 | Supplier Registry |
| M-007 | Source / Tender Import Layer |
| M-008 | Tender Normalization Layer |
| M-009 | Tender Screening Engine |
| M-010 | Intake Summary / Prioritization |
| M-011 | Document Ingestion Layer |
| M-012 | Requirement Extraction from Tender Docs |
| M-013 | Compliance Matrix Builder |
| M-014 | Document Requirement Extractor |
| M-015 | Initial Tech Risk Flags |
| M-016 | Supplier Search |
| M-017 | RFQ Generator |
| M-018 | Supplier Communication Tracker |
| M-019 | TKP Repository |
| M-020 | Supplier Verification |
| M-021 | Quote Comparison Engine |
| M-022 | Cost Model Engine |
| M-023 | Cash Gap Calculator |
| M-024 | Financing Strategy Engine |
| M-025 | Finance Memo Builder |
| M-026 | Contract Risk Parser |
| M-027 | Integrated Risk Memo Builder |
| M-028 | CEO Approval Cockpit |
| M-029 | Bid Document Collector |
| M-030 | Bid Package Builder |
| M-031 | Bid Completeness Checker |
| M-032 | Submission Archive |
| M-033 | Tender Procedure Monitor |
| M-034 | Contract Negotiation Workspace |
| M-035 | Supplier Back-to-Back Contract Draft |
| M-036 | Execution Plan Builder |
| M-037 | Purchase Order Manager |
| M-038 | Supplier Progress Monitor |
| M-039 | Logistics Tracker |
| M-040 | Incident Register |
| M-041 | Acceptance Control |
| M-042 | Closing Docs Pack Builder |
| M-043 | Payment Tracker |
| M-044 | Claims Trigger Engine |
| M-045 | Deal Closure Report |
| M-046 | Postmortem Builder |
| M-047 | Supplier Rating Updater |
| M-048 | Knowledge Asset Builder |
| M-049 | Agent Registry |
| M-050 | Prompt / Schema Library |
| M-051 | Workflow Orchestrator |
| M-052 | Notification Layer |
| M-053 | Red Flag Registry |
| M-054 | Master Dashboard |
| M-055 | SaaS Productization Tracker |

## Interpretation Notes

- This lock governs canonical business identity, not current package names.
- Existing code may remain temporarily unreconciled while the repo goes through controlled recovery.
- Historical implementation docs remain useful, but they do not override this lock.
