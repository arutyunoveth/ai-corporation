# Supplier Relevance Scoring (Demo Layer)

## Purpose

Deterministic rule-based relevance scoring evaluates whether a 44-ФЗ procurement matches a specific supplier profile before deep analysis. This demo layer helps operators quickly assess which search results are worth pursuing without cloud LLM or external services.

## Architecture

### Components

| Component | File | Role |
|-----------|------|------|
| Supplier Profile Model | `src/modules/tender_operator_agent_demo/supplier_profile.py` | Pydantic models for supplier profile, criteria, risk preferences |
| Relevance Scoring Engine | `src/modules/tender_operator_agent_demo/relevance_scoring.py` | Deterministic scoring rules, both card-level and document-level |
| Demo Fixture | `demo_data/tender_operator_agent/supplier_profile_electrical.json` | Demo electrical equipment supplier profile |
| Integration | `src/modules/tender_operator_agent_demo/procurement_discovery.py` | Relevance scores embedded in `search_public_44fz()` response |
| Document Scoring | `src/modules/tender_operator_agent_demo/upload_service.py` | Document-level relevance pass after archive extraction |
| UI | `src/modules/tender_operator_agent_demo/ui.py` | Score display on search cards, profile panel tab |

### Scoring Dimensions (Card-Level)

| Dimension | Max Points | Description |
|-----------|-----------|-------------|
| Keywords | 40 | Title contains supplier's keywords (stem/prefixed matching) |
| Price Range | 20 | Initial price within supplier's min/max range |
| Deadline | 10 | Submission deadline is reasonable (partial score when unknown) |
| Risk | 15 | Base score; risk flag detection (stub) |
| Stop Words | -15 each | Title contains supplier's stop words |

Score thresholds: High >= 65, Medium >= 40, Low >= 20, Not Recommended < 20.

### Document-Level Scoring

After archive extraction, extracted text is scored against the supplier profile:
- Keyword and certificate terms matched in document text
- Each match contributes 10 points (capped at 100)
- Results stored in run metadata as `document_relevance`

## Profile Management

- Default demo profile: electrical equipment supplier (Москва/МО, 100k–15M RUB)
- Reset via UI: "Профиль поставщика" tab → "Сбросить профиль"
- API: `GET /api/demo/tender-agent/supplier-profile`, `POST /api/demo/tender-agent/supplier-profile/reset`
- Profile is session-only (in-memory), not persisted

## Integration Points

1. **Search**: `search_public_44fz()` embeds `relevance` dict in each card
2. **Search Result Handoff**: relevance events logged
3. **Archive Extraction**: `analyze_uploaded_demo_run()` runs document scoring
4. **Run Response**: `document_relevance` field in `TenderOperatorUploadedRunResponse`

## Constraints

- Deterministic only — no ML, no LLM, no cloud
- Stem-based matching handles basic Russian morphology (7-char prefix + substring)
- All scores are demo-quality placeholders; real production scoring would differ
- No user authentication; profile reset via in-memory module-level cache
