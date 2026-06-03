# Sprint 1 Implementation Summary

## Scope

Sprint 1 formalizes the shared backend foundation for:

- `M-001` Deal Registry
- `M-002` Status Model Engine
- `M-003` Document Store
- `M-004` Event Log & Decision Journal

This iteration covers:

- repository structure
- modular backend skeleton
- canonical entity model
- migrations and seed data
- enums and business ID generators
- DTO/schema contracts
- services and API routes
- integration tests

## Assumptions

1. New deals start in `NEW`, because both the Sprint 1 technical spec and entity catalog show `NEW` as the baseline status.
2. Business ID generation uses the latest persisted sequence per prefix/year and relies on DB uniqueness as the guardrail for Sprint 1 concurrency.
3. Event and decision records stay in separate append-only tables, because these are the canonical Sprint 1 entities fixed in the catalog.
4. Tests run on SQLite for speed, while the default runtime and migration workflow target PostgreSQL.

## Tech Decisions

- `FastAPI` keeps the HTTP layer explicit and low-overhead.
- `SQLAlchemy 2` gives us a clear modular monolith data layer without forcing a heavy framework.
- `Alembic` formalizes the migration order required by the documents.
- `Pydantic` keeps DTO and validation contracts schema-first.
- `pytest` covers the Sprint 1 invariants as integration tests.

