from __future__ import annotations

import json
import math
from pathlib import Path

_GIB = 1024 ** 3


def _gib(n: int | float) -> float:
    return round(n / _GIB, 2)


def _round_up_gib(n: float | int) -> int:
    g = n / _GIB
    return int(math.ceil(g / 10.0)) * 10


def _validate_assumption(key: str, value: object):
    if not isinstance(value, (int, float)):
        return
    if value < 0:
        raise ValueError(f"negative assumption not allowed: {key}={value}")
    if key == "free_space_reserve_percent" and value >= 100:
        raise ValueError(
            f"free_space_reserve_percent must be < 100, got {value}"
        )


def _p(param: dict) -> float:
    return float(param["value"])


def load_scenarios(path: str) -> dict:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    profiles = raw.get("profiles", {})

    for pname, pdata in profiles.items():
        for key, val in pdata.items():
            if isinstance(val, dict) and "value" in val:
                _validate_assumption(key, val["value"])

    return raw


def compute_forecast(
    database_bytes: int | None,
    filesystem_bytes: dict[str, int] | None,
    assumptions: dict,
    years: int,
) -> dict:
    p = assumptions

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

    primary_storage = database_storage + persistent_file_storage

    estimated_full_backup_size = primary_storage * p["backup_compression_ratio"]
    backup_storage = estimated_full_backup_size * p["full_backups_retained"]

    temporary_storage = primary_storage * p["temporary_space_peak_factor"]

    raw_required = primary_storage + backup_storage + temporary_storage + p["operational_margin_bytes"]

    reserve_pct = p["free_space_reserve_percent"]
    recommended_disk = raw_required / (1 - reserve_pct / 100)
    rounded_recommended = _round_up_gib(recommended_disk)

    breakdown = {
        "years": years,
        "procurements": int(procurements),
        "analysis_runs": int(runs),
        "database_storage": {
            "bytes": int(database_storage),
            "gib": _gib(database_storage),
            "components": {
                "non_vector_metadata": {"bytes": int(db_non_vector), "gib": _gib(db_non_vector)},
                "vector_embeddings": {"bytes": int(vector_storage), "gib": _gib(vector_storage)},
            },
        },
        "persistent_file_storage": {
            "bytes": int(persistent_file_storage),
            "gib": _gib(persistent_file_storage),
            "components": {
                "raw_documents": {"bytes": int(raw_document_storage), "gib": _gib(raw_document_storage)},
                "extracted_texts": {"bytes": int(extracted_text_storage), "gib": _gib(extracted_text_storage)},
                "report_artifacts": {"bytes": int(report_artifact_storage), "gib": _gib(report_artifact_storage)},
                "other_artifacts": {"bytes": int(other_artifact_storage), "gib": _gib(other_artifact_storage)},
            },
        },
        "primary_storage": {"bytes": int(primary_storage), "gib": _gib(primary_storage)},
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

    if database_bytes is not None:
        measured_db_gib = round(database_bytes / _GIB, 2)
        breakdown["database_storage"]["measured_bytes"] = database_bytes
        breakdown["database_storage"]["measured_gib"] = measured_db_gib

    if filesystem_bytes is not None:
        total_fs = sum(filesystem_bytes.values())
        measured_fs_gib = round(total_fs / _GIB, 2)
        breakdown["persistent_file_storage"]["measured_bytes"] = total_fs
        breakdown["persistent_file_storage"]["measured_gib"] = measured_fs_gib

    return breakdown


def run_forecast(
    snapshot: dict | None,
    scenarios_path: str,
    years_list: list[int],
) -> dict:
    scenarios = load_scenarios(scenarios_path)
    profiles = scenarios.get("profiles", {})

    database_bytes = None
    filesystem_bytes = {}
    if snapshot:
        db = snapshot.get("database", {})
        if db.get("available") and db.get("database_size_bytes") is not None:
            database_bytes = db["database_size_bytes"]
        fs_list = snapshot.get("filesystem", [])
        for entry in fs_list:
            if entry.get("available") and entry.get("logical_bytes") is not None:
                filesystem_bytes[entry["root_name"]] = entry["logical_bytes"]

    results: dict = {
        "schema_version": "1.0",
        "scenario_source": scenarios_path,
        "snapshot_source": getattr(snapshot, "get", lambda x: None)("generated_at_utc"),
        "profiles": {},
    }

    for pname, pdata in profiles.items():
        params = {}
        for key, val in pdata.items():
            if isinstance(val, dict) and "value" in val:
                params[key] = val["value"]
            elif key != "description":
                params[key] = val if not isinstance(val, dict) else val.get("value", 0)

        profile_results: dict = {
            "description": pdata.get("description", ""),
            "projections": {},
        }
        for years in years_list:
            projection = compute_forecast(database_bytes, filesystem_bytes, params, years)
            profile_results["projections"][f"{years}_year"] = projection
        results["profiles"][pname] = profile_results

    return results
