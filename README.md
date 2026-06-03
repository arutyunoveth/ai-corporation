# ai-corporation

Sprint 1 foundation for the AI Corporation tender business platform. This iteration implements the core backend skeleton for:

- `M-001` Deal Registry
- `M-002` Status Model Engine
- `M-003` Document Store
- `M-004` Event Log & Decision Journal

The implementation follows the source-of-truth documents committed under `docs/`.

## Sprint 1 Scope

- canonical deal records with `deal_id`
- formal status transitions and append-only history
- artifact storage metadata with versioning and links
- append-only event and decision journals
- FastAPI endpoints, Alembic migrations, seed data, and integration tests

## Implementation Summary

- Stack: `FastAPI + SQLAlchemy 2 + Alembic + Pydantic + pytest`
- Runtime target: PostgreSQL
- Test runtime: SQLite in-memory for fast integration coverage
- Default status on create: `NEW`
- Business IDs are generated in application code with DB uniqueness guarantees and retry-friendly formatting:
  - `DL-YYYY-NNNNNN`
  - `ART-YYYY-NNNNNN`
  - `EVT-YYYY-NNNNNN`
  - `DEC-YYYY-NNNNNN`

## Repository Layout

```text
docs/
  00_architecture/
  01_sprints/
  02_modules/
  03_entities/
src/
  modules/
  shared/
migrations/
tests/
```

## Local Run

1. Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

2. Start PostgreSQL:

```bash
docker compose up -d
```

3. Export the database URL:

```bash
export AI_CORP_DATABASE_URL=postgresql+psycopg://ai_corporation:ai_corporation@localhost:5432/ai_corporation
```

4. Apply migrations:

```bash
alembic upgrade head
```

5. Run the API:

```bash
uvicorn src.main:app --reload
```

## Tests

```bash
pytest
```

## Implemented Endpoints

- `POST /deals`
- `GET /deals`
- `GET /deals/{deal_id}`
- `PATCH /deals/{deal_id}`
- `POST /status/validate-transition`
- `POST /status/apply-transition`
- `GET /status/history/{deal_id}`
- `POST /artifacts`
- `POST /artifacts/{artifact_ref}/versions`
- `GET /artifacts/{artifact_ref}`
- `GET /artifacts/{artifact_ref}/versions`
- `POST /artifacts/{artifact_ref}/links`
- `POST /events`
- `POST /decisions`
- `GET /events`
- `GET /decisions`

## Source Of Truth

- [docs/00_architecture/Unified_Module_Registry.md](/Users/master/Documents/AI-Corporation/docs/00_architecture/Unified_Module_Registry.md)
- [docs/00_architecture/Module_Dependency_Map_and_MVP_Core.md](/Users/master/Documents/AI-Corporation/docs/00_architecture/Module_Dependency_Map_and_MVP_Core.md)
- [docs/01_sprints/MVP_First_Wave_Roadmap_and_High_Level_Spec.md](/Users/master/Documents/AI-Corporation/docs/01_sprints/MVP_First_Wave_Roadmap_and_High_Level_Spec.md)
- [docs/01_sprints/MVP_First_Wave_Backlog.md](/Users/master/Documents/AI-Corporation/docs/01_sprints/MVP_First_Wave_Backlog.md)
- [docs/01_sprints/Sprint_1_Technical_Spec.md](/Users/master/Documents/AI-Corporation/docs/01_sprints/Sprint_1_Technical_Spec.md)
- [docs/03_entities/Entity_Catalog_Sprint_1.md](/Users/master/Documents/AI-Corporation/docs/03_entities/Entity_Catalog_Sprint_1.md)
