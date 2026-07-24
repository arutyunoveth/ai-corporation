# R9.4 final-PDF publication concurrency

Status: pending final disposable evidence run.

The PostgreSQL contract is split deliberately: the R8 integration test uses two barrier-synchronised identical `%PDF-` candidates and requires 2×201; the R9.4 integration test uses equal-size, distinct-SHA-256 candidates and requires `{201, 409}`. Both tests use independent FastAPI request sessions, one artifact generation, one PilotArtifact, one PilotRunResult, and one `artifact_exported` event. A sequential replay returns the winner without a third render.

The customer-pilot publisher passes `allow_existing_verified=False` for the first-publication filesystem race: existing generation validation includes both candidate SHA-256 and byte size. The pre-existing DB artifact path remains the R9.3 sequential replay path.
