# R10.1 / ARV-003 — Production LLM Analysis

Status: `R10_1_GATE_1_COMPLETE_GATE_2_READY`.

Canonical base: annotated tag `r9-operational-hardening-2026-07-24`, peeled commit `58bef2da2342bff1e6f63215ee2697e96fefe6f7`.

Architecture contract: `docs/reviews/r10-1-production-llm-architecture-audit-20260725.md`.

## Definition of done

ARV-003 is complete when one configured real provider processes a controlled real procurement through a versioned R10.1 producer and produces a canonical-compatible result where:

- every accepted factual conclusion resolves to evidence owned by the procurement;
- confidence is assigned by a deterministic grounding policy rather than trusted from the provider;
- provider/model/prompt/schema/evidence/policy identities are recorded;
- provider failure, invalid output, unsupported claims and budget exhaustion fail closed;
- token, latency and cost measurements are captured against explicit budgets;
- no stub or synthetic positive output is used in production mode;
- R8/R9 snapshot, hash, ownership, idempotency and final-PDF contracts remain unchanged;
- sanitized executable evidence is published for the real run.

## Gates

### Gate 0 — R9 closure

- [x] PR #16 synchronized with `main`;
- [x] final PR CI green;
- [x] Draft removed;
- [x] merged to `main`;
- [x] post-merge CI green;
- [x] annotated release tag created and verified.

Status: `R9_OPERATIONAL_HARDENING_MERGED_TAGGED_AND_POST_MERGE_VERIFIED`.

### Gate 1 — architecture audit and contract

- [x] inventory current controlled-provider, Hermes and RAG paths;
- [x] identify the frozen R9 canonical integration boundary;
- [x] define provider-neutral request/result/evidence contracts;
- [x] define fail-closed rules;
- [x] define confidence ownership;
- [x] define token/latency/cost budget requirements;
- [x] define ordered implementation plan and acceptance matrix.

Status: `R10_1_GATE_1_ARCHITECTURE_AUDIT_COMPLETE_IMPLEMENTATION_NOT_STARTED`.

### Gate 2 — offline production contract

- [ ] add `src/modules/production_llm_analysis/schemas.py`;
- [ ] add deterministic evidence-packet builder with stable SHA-256 identity;
- [ ] add claim-level grounding validator;
- [ ] validate exact quote and locator against current-procurement evidence;
- [ ] separate provider-reported and validator-derived confidence;
- [ ] add budget preflight and usage/latency/cost result models;
- [ ] add sanitized failure result contract;
- [ ] add a fake provider only for tests;
- [ ] prove no network is used in this gate;
- [ ] prove no source graph, canonical persistence, artifact, UI, deployment or 223-FZ change.

Required evidence:

- focused contract and validator tests;
- cross-procurement citation rejection;
- missing-quote rejection;
- unsupported-positive-decision rejection;
- timeout, invalid response and budget-exceeded fail-closed tests;
- deterministic request/evidence/policy identity tests;
- full `make check` and `make test` green.

### Gate 3 — one transport behind the contract

- [ ] extract or wrap one configured JSON provider transport behind the new interface;
- [ ] retain existing credential and raw-response safety defaults;
- [ ] capture provider/model/request identity and usage metadata;
- [ ] enforce timeout, retries and analysis-wide budgets;
- [ ] test with a mocked HTTP boundary only;
- [ ] prohibit production fallback to stub.

Provider selection and real credentials are not part of Gate 2.

### Gate 4 — versioned R10.1 canonical producer

- [ ] add a producer beside `produce_frozen_canonical_analysis()` rather than changing the frozen producer in place;
- [ ] pass only validated supported claims into the existing canonical output builder;
- [ ] preserve source graph construction and R8/R9 persistence formats;
- [ ] preserve immutable ownership, hashes, idempotency and final-PDF verification;
- [ ] make R9 versus R10.1 mode selection explicit and fail closed;
- [ ] reject canonical publication when grounding validation fails.

### Gate 5 — controlled real-provider evidence

- [ ] run one approved real procurement through the configured provider;
- [ ] verify every accepted claim against owned evidence;
- [ ] record evidence coverage and rejected claims;
- [ ] record provider/model/prompt/schema/policy versions;
- [ ] record token usage, latency and cost;
- [ ] prove budget compliance;
- [ ] publish sanitized CI/runtime evidence without raw tender data or credentials;
- [ ] repeat the same input to verify stable identities and non-conflicting publication.

### Gate 6 — handoff to ARV-001

- [ ] provide R10.1 evidence to the golden report and release-gate work;
- [ ] do not begin ARV-004 self-improvement or ARV-005 pilot expansion before ARV-001 acceptance criteria are defined.

## Non-goals

- no source graph redesign;
- no R8/R9 artifact-contract redesign;
- no new UI;
- no deployment;
- no 223-FZ;
- no provider marketplace or multi-provider benchmark;
- no Hermes customer-scoped memory/self-improvement work;
- no autonomous external action;
- no broad refactor of unrelated historical LLM code.

## Immediate next slice

Gate 2 is the only authorized implementation slice after this audit. It must remain provider-neutral and network-free. A real provider call is prohibited until the offline grounding and budget contracts are executable and green.