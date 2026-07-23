from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

_GIB = 1024 ** 3

_REQUIRED_PARAMS = frozenset({
    "procurements_per_month",
    "analysis_runs_per_procurement",
    "documents_per_procurement",
    "raw_document_bytes_per_procurement",
    "extracted_text_bytes_per_procurement",
    "chunks_per_procurement",
    "vector_dimension",
    "vector_bytes_per_component",
    "embedding_rows_per_chunk",
    "report_artifact_bytes_per_run",
    "other_artifact_bytes_per_run",
    "database_non_vector_bytes_per_procurement",
    "database_non_vector_bytes_per_run",
    "full_backups_retained",
    "backup_compression_ratio",
    "temporary_space_peak_factor",
    "operational_margin_bytes",
    "free_space_reserve_percent",
})

_REQUIRED_PROFILES = frozenset({"pilot", "commercial_mvp", "scaling"})


def _gib(n: int | float) -> float:
    return round(n / _GIB, 2)


def _round_up_gib(n: float | int) -> int:
    g = n / _GIB
    return int(math.ceil(g / 10.0)) * 10


def _validate_value(key: str, value: object, source: str):
    if isinstance(value, bool):
        raise ValueError(f"parameter {key} must be numeric, got bool")
    if not isinstance(value, (int, float)):
        raise ValueError(f"parameter {key} must be numeric, got {type(value).__name__}")
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"parameter {key} is NaN or Infinity")
    if value < 0:
        raise ValueError(f"negative assumption not allowed: {key}={value}")
    if key == "free_space_reserve_percent":
        if value >= 100:
            raise ValueError(f"free_space_reserve_percent must be < 100, got {value}")
    if key == "backup_compression_ratio":
        if not (0 < value <= 1):
            raise ValueError(f"backup_compression_ratio must be in (0, 1], got {value}")
    if key == "temporary_space_peak_factor":
        if value < 0:
            raise ValueError(f"temporary_space_peak_factor must be >= 0, got {value}")
    if key == "years":
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"years must be a positive integer, got {value}")


def load_scenarios(path: str) -> dict:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    profiles = raw.get("profiles", {})

    for pname in _REQUIRED_PROFILES:
        if pname not in profiles:
            raise ValueError(f"required profile missing: {pname}")

    for pname, pdata in profiles.items():
        for key in _REQUIRED_PARAMS:
            if key not in pdata:
                raise ValueError(f"profile {pname} missing required parameter: {key}")
            val = pdata[key]
            if isinstance(val, dict):
                v = val.get("value")
                s = val.get("source", "")
                _validate_value(key, v, s)
                if s != "assumption":
                    raise ValueError(
                        f"profile {pname} parameter {key} source must be 'assumption', got '{s}'"
                    )
            else:
                _validate_value(key, val, "input")

        if "documents_per_procurement" in pdata:
            pdata["_documents_per_procurement_note"] = "informational — not used in storage calculations"

    return raw


def _compute_incremental(p: dict, years: int) -> dict:
    procurements = p["procurements_per_month"] * 12 * years
    runs = procurements * p["analysis_runs_per_procurement"]

    vector_bytes_per_row = p["vector_dimension"] * p["vector_bytes_per_component"]
    vector_storage = procurements * p["chunks_per_procurement"] * p["embedding_rows_per_chunk"] * vector_bytes_per_row

    db_non_vector = (
        procurements * p["database_non_vector_bytes_per_procurement"]
        + runs * p["database_non_vector_bytes_per_run"]
    )

    database_storage = db_non_vector + vector_storage

    raw_document_storage = procurements * p["raw_document_bytes_per_procurement"]
    extracted_text_storage = procurements * p["extracted_text_bytes_per_procurement"]
    report_artifact_storage = runs * p["report_artifact_bytes_per_run"]
    other_artifact_storage = runs * p["other_artifact_bytes_per_run"]
    persistent_file_storage = (
        raw_document_storage
        + extracted_text_storage
        + report_artifact_storage
        + other_artifact_storage
    )

    return {
        "procurements": int(procurements),
        "analysis_runs": int(runs),
        "database_bytes": int(database_storage),
        "file_bytes": int(persistent_file_storage),
        "components": {
            "db_non_vector": int(db_non_vector),
            "db_vector": int(vector_storage),
            "raw_documents": int(raw_document_storage),
            "extracted_texts": int(extracted_text_storage),
            "report_artifacts": int(report_artifact_storage),
            "other_artifacts": int(other_artifact_storage),
        },
    }


def compute_forecast(
    baseline_database_bytes: int | None,
    baseline_filesystem_bytes: int | None,
    assumptions: dict,
    years: int,
) -> dict:
    p = assumptions
    inc = _compute_incremental(p, years)

    db_baseline = baseline_database_bytes if baseline_database_bytes is not None else 0
    fs_baseline = baseline_filesystem_bytes if baseline_filesystem_bytes is not None else 0

    db_source = "measured" if baseline_database_bytes is not None else "unavailable"
    fs_source = "measured" if baseline_filesystem_bytes is not None else "unavailable"

    projected_database = db_baseline + inc["database_bytes"]
    projected_filesystem = fs_baseline + inc["file_bytes"]

    primary_storage = projected_database + projected_filesystem

    estimated_full_backup_size = primary_storage * p["backup_compression_ratio"]
    backup_storage = estimated_full_backup_size * p["full_backups_retained"]

    temporary_storage = primary_storage * p["temporary_space_peak_factor"]

    raw_required = primary_storage + backup_storage + temporary_storage + p["operational_margin_bytes"]

    reserve_pct = p["free_space_reserve_percent"]
    recommended_disk = raw_required / (1 - reserve_pct / 100)
    rounded_recommended = _round_up_gib(recommended_disk)

    inc_bytes = inc["database_bytes"]
    inc_fs_bytes = inc["file_bytes"]

    breakdown = {
        "years": years,
        "procurements": inc["procurements"],
        "analysis_runs": inc["analysis_runs"],
        "database_storage": {
            "baseline_bytes": db_baseline,
            "baseline_gib": _gib(db_baseline),
            "baseline_source": db_source,
            "incremental_bytes": inc_bytes,
            "incremental_gib": _gib(inc_bytes),
            "projected_total_bytes": projected_database,
            "projected_total_gib": _gib(projected_database),
            "components": {
                "non_vector_metadata": {
                    "incremental_bytes": inc["components"]["db_non_vector"],
                    "incremental_gib": _gib(inc["components"]["db_non_vector"]),
                },
                "vector_embeddings": {
                    "incremental_bytes": inc["components"]["db_vector"],
                    "incremental_gib": _gib(inc["components"]["db_vector"]),
                },
            },
        },
        "persistent_file_storage": {
            "baseline_bytes": fs_baseline,
            "baseline_gib": _gib(fs_baseline),
            "baseline_source": fs_source,
            "incremental_bytes": inc_fs_bytes,
            "incremental_gib": _gib(inc_fs_bytes),
            "projected_total_bytes": projected_filesystem,
            "projected_total_gib": _gib(projected_filesystem),
            "components": {
                "raw_documents": {
                    "incremental_bytes": inc["components"]["raw_documents"],
                    "incremental_gib": _gib(inc["components"]["raw_documents"]),
                },
                "extracted_texts": {
                    "incremental_bytes": inc["components"]["extracted_texts"],
                    "incremental_gib": _gib(inc["components"]["extracted_texts"]),
                },
                "report_artifacts": {
                    "incremental_bytes": inc["components"]["report_artifacts"],
                    "incremental_gib": _gib(inc["components"]["report_artifacts"]),
                },
                "other_artifacts": {
                    "incremental_bytes": inc["components"]["other_artifacts"],
                    "incremental_gib": _gib(inc["components"]["other_artifacts"]),
                },
            },
        },
        "primary_storage": {
            "projected_total_bytes": int(primary_storage),
            "projected_total_gib": _gib(primary_storage),
        },
        "backup_storage": {"bytes": int(backup_storage), "gib": _gib(backup_storage)},
        "temporary_storage": {"bytes": int(temporary_storage), "gib": _gib(temporary_storage)},
        "operational_margin": {
            "bytes": int(p["operational_margin_bytes"]),
            "gib": _gib(p["operational_margin_bytes"]),
        },
        "raw_required": {"bytes": int(raw_required), "gib": _gib(raw_required)},
        "free_space_reserve_percent": reserve_pct,
        "recommended_disk_bytes": int(rounded_recommended * _GIB),
        "recommended_disk_gib": rounded_recommended,
    }

    return breakdown


def run_forecast(
    snapshot: dict | None,
    scenarios_path: str,
    years_list: list[int],
) -> dict:
    scenarios = load_scenarios(scenarios_path)
    profiles = scenarios.get("profiles", {})

    baseline_database_bytes: int | None = None
    baseline_filesystem_bytes: int | None = None
    snapshot_meta: dict | None = None

    if snapshot:
        db = snapshot.get("database", {})
        if db.get("available") and db.get("database_size_bytes") is not None:
            baseline_database_bytes = db["database_size_bytes"]
        from scripts.capacity.fs_collector import resolve_unique_fs_bytes
        fs_list = snapshot.get("filesystem", [])
        baseline_filesystem_bytes = resolve_unique_fs_bytes(fs_list)
        snapshot_meta = {
            "generated_at_utc": snapshot.get("generated_at_utc"),
            "git_commit": snapshot.get("git_commit"),
            "schema_version": snapshot.get("schema_version"),
        }

    scenario_name = Path(scenarios_path).name
    scenario_bytes = Path(scenarios_path).read_bytes() if Path(scenarios_path).exists() else b""
    scenario_sha = hashlib.sha256(scenario_bytes).hexdigest()[:16]

    results: dict = {
        "schema_version": "1.1",
        "scenario_source": {
            "file_name": scenario_name,
            "sha256": scenario_sha,
            "source": "input",
        },
        "snapshot_source": snapshot_meta,
        "profiles": {},
    }

    for pname, pdata in profiles.items():
        params = {}
        for key, val in pdata.items():
            if isinstance(val, dict) and "value" in val:
                params[key] = val["value"]
            elif key not in ("description", "_documents_per_procurement_note"):
                params[key] = val if not isinstance(val, dict) else val.get("value", 0)

        profile_results: dict = {
            "description": pdata.get("description", ""),
            "projections": {},
        }
        for years in years_list:
            projection = compute_forecast(
                baseline_database_bytes, baseline_filesystem_bytes, params, years
            )
            profile_results["projections"][f"{years}_year"] = projection
        results["profiles"][pname] = profile_results

    return results
