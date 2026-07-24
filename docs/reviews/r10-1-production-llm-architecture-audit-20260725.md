# R10.1 / ARV-003 — production LLM architecture audit

Status: `R10_1_GATE_1_ARCHITECTURE_AUDIT_COMPLETE_IMPLEMENTATION_NOT_STARTED`.

Baseline:

- frozen R9 tag: `r9-operational-hardening-2026-07-24`;
- tag object: `556cf2d019ea5727057ce39e8819514b469415bf`;
- peeled R9 merge commit: `58bef2da2342bff1e6f63215ee2697e96fefe6f7`;
- post-merge CI: workflow run `30126466076`, all five jobs successful.

This document is a read-only source audit and an implementation contract. It does not connect an external provider and does not change runtime behaviour.

## 1. End goal

R10.1 must connect a real configured LLM provider to the frozen R9 analysis pipeline and produce a reproducible, evidence-grounded procurement analysis with:

- claim-level source citations;
- explicit confidence semantics;
- fail-closed behaviour;
- enforceable latency and cost budgets;
- rejection of unsupported conclusions;
- provider, model, prompt and schema provenance;
- no change to the R8/R9 immutable artifact and ownership contracts.

R10.1 is complete only when a real procurement can be processed through a production provider and every accepted conclusion can be resolved to evidence owned by that procurement.

## 2. Scope boundaries

The following are explicitly outside this work:

- changing `ProcurementSourceGraph` construction or reconciliation;
- changing R8/R9 canonical snapshot, hash, immutable artifact or ownership contracts;
- changing the business model;
- adding a new UI;
- adding 223-FZ;
- deployment or VPS work;
- Hermes customer-scoped feedback and self-improvement, which belongs to ARV-004;
- the full golden release gate, which belongs to ARV-001;
- the 10–20 procurement pilot, which belongs to ARV-005;
- autonomous supplier outreach, submission, signing or other external execution.

## 3. Current LLM-related paths in `main`

The repository currently contains three useful but disconnected LLM paths. None by itself satisfies ARV-003.

### 3.1 Controlled pre-bid provider layer

`src/modules/controlled_llm_prebid/service.py` contains real transport implementations for:

- OpenAI-compatible APIs;
- Yandex AI Studio / Alice aliasing;
- GigaChat OAuth plus chat completion;
- Cloud.ru OpenAI-compatible API.

It already provides:

- provider selection through settings;
- temperature `0`;
- timeout and bounded retry count;
- Pydantic schema validation;
- optional input redaction;
- raw-response suppression by default;
- runtime control traces;
- mandatory human-review disposition;
- forbidden autonomous external actions in prompt and agent metadata.

However, its section schemas contain prose and lists without claim-level evidence references or confidence. A failed section is recorded as validation failed, but the workflow continues and returns a partially populated result. It does not enforce an analysis-wide latency, token or cost budget. Provider usage metadata is not captured. The private provider classes are coupled to the pre-bid module and are not yet a production provider contract.

Conclusion: this path is the best transport implementation to extract later, but it is not safe to connect directly to the frozen R9 canonical producer.

### 3.2 Hermes runtime analysis

`src/modules/hermes_agent/client.py`, `schemas.py`, `service.py` and `quality.py` already provide:

- structured line items, technical requirements, certification requirements and risks;
- `source_document`, `source_quote`, locator fields and per-field confidence on several output types;
- evidence coverage metrics;
- quality gates;
- one improvement attempt;
- persistence of evidence spans;
- analysis duration;
- deterministic normalization, NMCK mapping and supplier-readiness post-processing.

The current Hermes client is an HTTP client for a separate Hermes service, not a provider abstraction. Provider/model/prompt provenance, token usage and cost are absent. Evidence validation is incomplete:

- high-confidence evidence is required only above the current threshold;
- a source quote is not proven to be an exact span in the owned source text;
- document-name references are not uniformly resolved to an owned document for all claim types;
- confidence is accepted from the response rather than derived from validated evidence;
- citation coverage counts populated fields, not semantic support for each conclusion.

The availability fallback is also unsuitable for production acceptance. When Hermes is unavailable, the fallback may return `ready` when no specification role is detected. Production ARV-003 must never turn provider unavailability into a positive readiness state.

Conclusion: Hermes schemas and quality concepts are useful inputs, but `HermesClient` must not become the authoritative production provider contract. Hermes production-loop memory and self-improvement remain ARV-004 work after ARV-003 is stable.

### 3.3 Local RAG chat

`src/tender_research/rag/llm.py` provides:

- retrieval-backed source objects with document and chunk identity;
- quote previews and retrieval scores;
- a context-character budget;
- temperature `0`;
- fail-safe answers for missing context, timeout and malformed responses;
- explicit prompt rules to answer only from supplied fragments.

Its citations are attached from the retrieved context set rather than bound to individual claims. The answer remains free-form text. It does not validate that each answer sentence is supported by a cited chunk and does not expose confidence, provider usage or cost.

Conclusion: `SourceCitation` and retrieval context construction are useful building blocks for the production evidence packet, but the current RAG answer contract is not the ARV-003 output contract.

## 4. Frozen R9 integration boundary

The frozen customer-pilot flow is:

1. `customer_pilot.router.start_run()` creates a tenant-owned `TenderAnalysisRun`;
2. `complete_run()` calls `bind_completed_analysis()`;
3. `bind_completed_analysis()` resolves server-owned inputs and calls `produce_frozen_canonical_analysis()`;
4. `produce_frozen_canonical_analysis()` is the sole frozen R7 builder for `ProcurementSourceGraph` and `CanonicalProcurementModel`;
5. canonical bytes are verified, immutably published and bound to DB identities;
6. final PDF publication consumes the verified canonical snapshot.

The frozen producer currently sends empty requirements, risks, supplier questions and bid decision into the existing output builder. It does not call an LLM.

### Required seam

Do not modify the frozen R9 producer in place.

Add a parallel, versioned R10.1 producer after the provider contract is proven:

`resolve_customer_run_inputs` → deterministic evidence packet → production provider → grounding validator → existing canonical output builder → existing canonical persistence and verification.

The future R10.1 producer must preserve the exact R8/R9 storage, hash, ownership and PDF publication contracts. Selection between frozen R9 and R10.1 must be explicit and fail closed; it must not silently fall back from production LLM mode to stub or frozen positive analysis.

## 5. Production provider contract

The next implementation slice must introduce a provider-neutral contract before any real external call.

### 5.1 Request envelope

A `ProductionLLMAnalysisRequest` must contain at least:

- `request_id` derived deterministically from run identity, evidence-packet hash, prompt version, schema version, provider and model;
- `customer_id`, `project_id`, `procurement_case_id`, `run_id`, `registry_number`;
- immutable evidence-packet hash;
- bounded evidence fragments with owned document ID, chunk/locator and exact text;
- prompt ID and prompt version;
- output schema ID and schema version;
- configured provider and model;
- timeout;
- maximum input tokens;
- maximum output tokens;
- maximum total latency;
- maximum estimated cost and currency;
- data-handling mode and redaction report.

No secret, raw credential or unrestricted filesystem path may enter the request, trace or persisted result.

### 5.2 Evidence reference

Every factual claim eligible for canonical output must carry one or more `EvidenceReference` values:

- owned `document_id`;
- document display name;
- `chunk_id` or deterministic source locator;
- exact quote;
- quote SHA-256;
- optional table/row/cell locator;
- evidence-packet fragment ID.

A reference is valid only when the document belongs to the current procurement and the exact quote resolves inside the canonical evidence fragment identified by the locator. A provider-generated file name or quote is not sufficient.

### 5.3 Grounded claim

A `GroundedClaim` must contain:

- stable `claim_id`;
- canonical `field_path`;
- typed value;
- `support_status`: `supported`, `insufficient_evidence` or `rejected`;
- one or more evidence references for `supported` claims;
- provider-reported confidence retained only as untrusted metadata;
- validator-derived confidence and confidence basis;
- validation errors or limitations.

The grounding validator, not the provider, owns final support status and accepted confidence.

### 5.4 Result envelope

A `ProductionLLMAnalysisResult` must contain:

- `status`: `success`, `insufficient_evidence`, `provider_unavailable`, `timeout`, `budget_exceeded`, `invalid_response` or `validation_failed`;
- provider and model identity;
- provider request ID when available;
- prompt and schema versions;
- evidence-packet hash;
- validated claims;
- rejected claims and reasons;
- analysis-wide limitations;
- input/output token usage when reported;
- latency by attempt and total latency;
- estimated cost, currency and pricing-table version;
- retry count;
- sanitized error code;
- raw-response SHA-256 when a raw response exists;
- no raw response body by default.

## 6. Fail-closed rules

Production mode must obey all of the following:

1. No external context means no provider call and status `insufficient_evidence`.
2. Provider unavailability, timeout, malformed JSON or schema failure cannot produce `ready`, `GO` or any other positive decision.
3. Stub output is prohibited in production mode.
4. A factual claim without a resolvable owned evidence reference is rejected before canonical construction.
5. A section that fails validation cannot feed a dependent section.
6. A bid decision cannot be accepted when any decision-driving claim is rejected or insufficiently supported.
7. Budget preflight failure prevents the call. Runtime budget exhaustion stops further attempts or sections.
8. Retries are bounded and use the same idempotent request identity.
9. Raw provider errors are sanitized; credentials and raw partner data are never written to logs or traces.
10. Failure produces an explicit `needs_review` analysis state and limitations, not a synthetic positive analysis.
11. Canonical snapshot publication remains impossible unless the R10.1 result and all accepted claims pass the grounding validator.

## 7. Confidence semantics

Provider self-confidence must not be treated as truth.

R10.1 must persist two separate values when the provider supplies confidence:

- `provider_confidence`: untrusted provider metadata;
- `validated_confidence`: a deterministic value produced by the grounding policy.

The exact scoring rubric must be versioned and tested before the first real provider run. At minimum it must distinguish:

- direct exact evidence;
- deterministic derivation from multiple exact evidence spans;
- conflicting evidence;
- incomplete evidence;
- provider-only assertion.

Provider-only assertions receive no accepted confidence and cannot enter canonical factual output.

## 8. Latency, token and cost budgets

The production call path must enforce both per-request and per-analysis budgets.

Required controls:

- bounded evidence size before transport;
- maximum input and output tokens;
- per-attempt timeout;
- maximum retries;
- maximum total analysis latency;
- maximum estimated cost per analysis;
- versioned provider pricing configuration;
- usage reconciliation after the response;
- budget status in every result and trace.

If a provider does not report token usage, the result must state that usage is estimated. Unknown usage must not be represented as zero cost.

No provider price or budget value is selected by this audit. Those values must be explicit configuration with test fixtures, not hidden constants.

## 9. Determinism and reproducibility

A reproducible run must bind:

- exact evidence-packet hash;
- provider and model;
- provider parameters;
- prompt version;
- output schema version;
- grounding-policy version;
- request identity;
- response hash;
- validated result hash;
- usage, latency and budget outcome.

Temperature must remain `0`. This does not guarantee byte-identical provider output, so reproducibility means replayable inputs, versioned policy and verifiable evidence—not an unsupported promise of identical remote generations.

A repeated request with the same identity must not create conflicting canonical ownership. Existing R8/R9 idempotency and immutable publication checks remain authoritative.

## 10. Data handling

The existing regex redaction is useful but insufficient as the production policy by itself. R10.1 must make the outbound evidence packet explicit and allow-listed:

- send only fields required by the prompt contract;
- exclude credentials, local paths, internal comments and unrelated customer data;
- preserve evidence identities needed for validation;
- record redaction and field-selection metrics;
- store no raw response by default;
- never persist provider authorization headers;
- keep provider-specific transport details outside canonical business schemas.

## 11. Reuse and extraction decisions

### Reuse

- provider endpoint and authentication patterns from `controlled_llm_prebid`;
- Pydantic strict validation pattern;
- raw-response suppression and runtime trace concepts;
- RAG document/chunk citation identities;
- Hermes evidence-bearing business schemas where compatible;
- existing deterministic normalization, NMCK mapping and supplier-readiness calculations;
- R8/R9 canonical persistence, hashes, idempotency and immutable artifact verification.

### Do not reuse directly

- private pre-bid provider classes as the public production interface;
- Hermes availability fallback;
- free-form RAG answer as canonical analysis;
- provider-reported confidence as accepted confidence;
- partial section success as an overall successful analysis;
- stub fallback in production mode.

### Extraction target

After the contract tests are green, provider transport may be extracted into a neutral module such as `src/shared/llm/transport.py`. Business-level production contracts should live in a dedicated module such as `src/modules/production_llm_analysis/` and must not depend on tender-operator pilot schemas.

## 12. Acceptance matrix for the contract slice

The next slice is accepted only with executable tests for:

| Scenario | Required result |
| --- | --- |
| Valid fake-provider response with exact owned citations | `success`; all claims resolve; deterministic hashes stable |
| Claim cites another procurement's document | claim rejected; analysis `validation_failed` or `insufficient_evidence` |
| Quote is absent from cited fragment | claim rejected |
| Provider returns unsupported positive decision | decision rejected; final state `needs_review` |
| Provider timeout/unavailable | sanitized non-success result; no stub and no positive decision |
| Invalid JSON/schema | `invalid_response`; no canonical publication input |
| Input budget exceeded before call | provider not invoked; `budget_exceeded` |
| Total latency/cost budget exceeded during run | remaining work stopped; `budget_exceeded` |
| Same request inputs repeated | same request/evidence/policy identities |
| Raw response storage disabled | no raw body persisted; response hash and metadata retained |
| Credentials or local path in context | absent from provider request, result and trace |

No real network or credential is required for this contract slice.

## 13. Ordered implementation plan

1. `Gate 0` — canonical R9 close: complete.
2. `Gate 1` — architecture audit and production contract: complete by this document.
3. `Gate 2` — implement provider-neutral schemas, deterministic evidence packet, grounding validator, budgets and fake-provider tests. No network.
4. `Gate 3` — extract one configured provider transport behind the contract and add mocked transport tests. No real procurement call yet.
5. `Gate 4` — add a versioned R10.1 canonical producer beside the frozen R9 producer, preserving persistence and artifact contracts.
6. `Gate 5` — execute one controlled real-provider procurement, publish sanitized evidence, and measure citations, confidence, latency and cost.
7. `Gate 6` — hand the result to ARV-001 golden quality gates.

## 14. Gate 1 decision

The repository already contains enough transport, evidence and operational primitives to avoid a new framework. The safe path is consolidation behind a new production contract—not direct wiring of an existing pilot client into the frozen producer.

Implementation must begin with offline schemas and validators. Connecting credentials or a real provider before those gates exist would create an unverifiable path that cannot satisfy ARV-003.