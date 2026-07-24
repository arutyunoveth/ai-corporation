# Product Backlog

## Deferred Until After MVP v1

- SaaS hardening for multi-tenant deployment
- production auth and access-control layer
- deployment automation and operational packaging
- UI polish beyond the commercial operator skeleton
- procurement platform integrations
- supplier outbound automation
- EDS/signature workflow
- post-award commercialization and external execution

## Post-MVP Product Expansion: Supplier Catalog and Procurement Matching

This block is intentionally deferred until the current MVP and restricted pilot are completed and validated on real procurements. It is based on the BIMLIB/Radar/Spectrum product pattern: one normalized supplier catalog reused across search, matching, economics, reporting, and future monitoring.

### Entry Criteria

- current MVP quality gates remain stable on real procurements
- first restricted-pilot evidence and operator feedback are collected
- extraction and report quality are reliable enough that catalog matching will not amplify source errors
- current human-review and no-external-execution boundaries remain in force

### P0 — Supplier Profile v0

- [ ] create a canonical `SupplierProfile` domain object
- [ ] create `CatalogItem`, `CatalogItemAlias`, `CatalogItemCharacteristic`, `SupplierRegion`, and `SupplierConstraint` entities
- [ ] support XLSX and CSV catalog import with operator-confirmed column mapping
- [ ] support manual item creation and correction
- [ ] normalize manufacturer, brand, model, article, unit, OKPD2, KTRU, standards, price, lead time, minimum quantity, aliases, and technical characteristics
- [ ] store acceptable equivalents and explicit product limitations
- [ ] keep the first pilot scope bounded, for example up to 100 catalog items per supplier profile
- [ ] reuse the supplier profile in search relevance, document analysis, TKP workflows, economics, and reporting

### P0 — Procurement Match Map

- [ ] match each evidence-backed procurement line item against the supplier catalog
- [ ] support explicit match states: `EXACT`, `LIKELY_ANALOG`, `PARTIAL`, `UNCERTAIN`, `NO_MATCH`
- [ ] store confidence, matched characteristics, conflicting characteristics, source evidence, and explanation for every candidate match
- [ ] require operator confirmation before a match affects commercial calculations
- [ ] preserve procurement-row identity and prohibit silent merging of distinct source positions
- [ ] separate confirmed supplier coverage from unresolved and unsupported positions
- [ ] generate a position coverage matrix for Web, JSON, DOCX, and PDF reports

### P0 — Decision and Economics Screen

- [ ] show matched positions, unresolved positions, and missing coverage in one operator view
- [ ] quantify confirmed catalog coverage by item count, quantity, and monetary value
- [ ] connect confirmed matches to cost, logistics, security, tax, commission, target price, and margin calculations
- [ ] show evidence-backed technical, contract, commercial, delivery, and documentation risks
- [ ] support controlled outcomes: `GO`, `GO_AFTER_CLARIFICATION`, `NEEDS_REVIEW`, `NO_GO`
- [ ] generate supplier questions, RFQ actions, and next-step recommendations from unresolved gaps without automatic external dispatch

### P0 — Managed Catalog Onboarding and Pilot Packaging

- [ ] define an operator-led onboarding flow where a customer can provide an existing price list, catalog, website export, or mixed Excel files
- [ ] normalize the initial supplier catalog as a managed service rather than requiring self-service data preparation
- [ ] run several real procurements during onboarding and calibrate aliases, characteristics, and constraints
- [ ] package a bounded post-MVP pilot: one supplier profile, one user, limited SKU count, limited full analyses, and a final operator review
- [ ] measure relevance, false matches, extraction coverage, operator corrections, time-to-decision, detected critical risks, and potential matched value

### P1 — Monitoring and Notifications

- [ ] add recurring search based on the normalized supplier profile only after matching quality is validated
- [ ] deduplicate procurement opportunities across supported sources
- [ ] provide a daily or configurable operator queue of new relevant procurements
- [ ] add email and Telegram digests without automatic bid or supplier actions
- [ ] track procurement changes and re-evaluate affected match and risk results
- [ ] rank opportunities by confirmed coverage, commercial potential, deadline, and risk rather than by keyword similarity alone

### P1 — Product and Customer Analytics

- [ ] record which AI suggestions and catalog matches operators accept, reject, or correct
- [ ] record final participation decisions and known outcomes
- [ ] identify recurring extraction, matching, risk, and pricing failure patterns
- [ ] use accumulated corrections as a controlled quality-improvement dataset
- [ ] expose pilot metrics without presenting unverified estimates as facts

### P2 — Integrations

- [ ] add structured export for CRM, ERP, and internal customer systems
- [ ] provide a documented internal API only after the domain model is stable
- [ ] evaluate a browser extension or "Analyze in Arvectum" handoff for EIS and procurement-platform pages
- [ ] preserve API, webhook, and integration audit trails
- [ ] do not allow integrations to bypass operator approval or existing action gates

### P3 — Complementary Supplier Network

- [ ] evaluate matching uncovered procurement positions with complementary suppliers
- [ ] support controlled joint-offer workspaces with clear ownership of positions, prices, and documents
- [ ] calculate consolidated economics without exposing one supplier's protected commercial data to another by default
- [ ] maintain partner reliability and fulfillment history
- [ ] defer any marketplace, commission, referral-payment, or automated partner-contact model until legal and commercial validation

### Explicit Non-Goals for This Expansion Stage

- no autonomous bid submission
- no EDS/signature automation
- no uncontrolled supplier or customer messaging
- no advertising marketplace
- no CAD/BIM plugin development
- no AR model production
- no broad self-service multi-tenant product before restricted-pilot evidence justifies it
- no final legal or commercial decision without human review

## Open Follow-Ups

- consolidate remaining absolute local links in historical governance/launch docs without rewriting historical decisions
- add richer report export formats if customer demos require them
- define paid-pilot packaging and onboarding constraints after `C6`
- enrich the demo flow with bounded LLM-assisted analysis in `C3`, keeping deterministic fallback available
- evaluate richer schema families and provider abstraction hardening after `C3`, without broad runtime opening
- persist versioned supplier-request draft templates if commercial operators need reusable outbound packs
- add richer quote attachment parsing and validation while keeping manual registration as the safe default
- evaluate status-engine synchronization for commercial workspace actions without forcing unsafe automatic transitions
- [x] confirm that accepted local C1-C6 and CP0 state is published/synced to `origin/main` before external repository review (DP0)
- [x] add a minimal pilot-facing auth/access boundary before broader customer circulation (DP1)
- [x] create bounded partner workspace and safe data intake layer (DP2)
- [x] create safe redaction workflow for real tender materials (DP3)
- [x] create safe partner-facing report export and delivery flow (DP4)
- [x] create structured feedback and outcome loop for design-partner pilots (DP5)
- [x] run end-to-end design-partner pilot dry run (DP6)
- [x] complete paid pilot readiness review (DP7)
- [x] restricted paid pilot operations setup (PP0) — runbook, data policy, templates, checklist, gitignore
- [x] real partner tender folder runner (PP1) — local folder-based pilot command with folder validation, intake, redaction, analysis, export guard, and output generation
- [x] tender operator pilot runner refinement (PP1R) — RFQ-first workflow for tender/operator companies; calibrated contract risk; TKP comparison/economics; no product catalog assumptions
- collect first real design-partner/tender-operator evidence with real operator/customer feedback
- improve customer/export packaging for partner-facing report delivery without opening external execution
