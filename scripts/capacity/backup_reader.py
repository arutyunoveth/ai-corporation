from __future__ import annotations

import hashlib
import json
import os


_BACKUP_COMPONENTS = frozenset({
    "manifest.json",
    "database.dump",
    "artifacts.tar.gz",
    "SHA256SUMS",
})

_DEFAULT_BACKUP_SOURCE_NAMES = [
    "pilot-data", "data",
    "pilot-artifacts", "artifacts",
    "pilot-eis", "eis-archives", "pilot-eis-archives",
]


def analyze_backup(
    backup_dir: str,
    live_archive_source_bytes: int | None = None,
) -> dict:
    result: dict = {
        "available": False,
        "error": None,
        "warnings": [],
        "backup_dir_id": None,
        "components": {},
        "compression_ratio": None,
        "total_bytes": None,
        "total_gib": None,
    }
    if not os.path.isdir(backup_dir):
        result["error"] = {"code": "backup_dir_not_found", "error_type": "FileNotFoundError"}
        result["warnings"].append("backup directory not accessible")
        return result

    result["available"] = True
    result["backup_dir_id"] = _path_id_short(backup_dir)
    found = set()
    for fname in os.listdir(backup_dir):
        fpath = os.path.join(backup_dir, fname)
        if fname in _BACKUP_COMPONENTS and os.path.isfile(fpath):
            found.add(fname)
            try:
                sz = os.path.getsize(fpath)
            except OSError:
                sz = None
            entry: dict = {"file_name": fname, "byte_size": sz, "exists": True}
            if fname == "manifest.json" and sz is not None:
                try:
                    with open(fpath, "r", encoding="utf-8") as fh:
                        manifest = json.load(fh)
                    entry["manifest_metadata"] = _safe_manifest(manifest)
                except (json.JSONDecodeError, OSError) as exc:
                    result["warnings"].append(
                        {"code": "manifest_parse_failed", "error_type": type(exc).__name__}
                    )
            result["components"][fname] = entry

    for required in sorted(_BACKUP_COMPONENTS):
        if required not in found:
            result["components"][required] = {
                "file_name": required,
                "byte_size": None,
                "exists": False,
            }
            result["warnings"].append(
                {"code": "missing_backup_component", "error_type": "FileNotFoundError"}
            )

    total = 0
    has_all = True
    for comp in result["components"].values():
        bs = comp.get("byte_size")
        if bs is not None:
            total += bs
        else:
            has_all = False
    if has_all:
        result["total_bytes"] = total
        result["total_gib"] = round(total / (1024**3), 2)

    art_comp = result["components"].get("artifacts.tar.gz", {})
    art_bytes = art_comp.get("byte_size")
    if art_bytes is not None and art_bytes > 0 and live_archive_source_bytes is not None and live_archive_source_bytes > 0:
        ratio = art_bytes / live_archive_source_bytes
        result["compression_ratio"] = round(ratio, 4)
        result["warnings"].append(
            {"code": "single_snapshot_ratio", "error_type": "Warning"}
        )
    return result


def _path_id_short(abs_path: str) -> str:
    return hashlib.sha256(abs_path.encode("utf-8")).hexdigest()[:16]


def _safe_manifest(manifest: dict) -> dict:
    safe_keys = {
        "schema_version", "generated_at", "backup_version", "database_name",
        "tables_count", "total_size_bytes", "file_count", "artifact_count",
        "compression", "notes",
    }
    return {k: v for k, v in manifest.items() if k in safe_keys}


def resolve_backup_source_names(provided: list[str] | None) -> list[str]:
    if provided:
        return provided
    return _DEFAULT_BACKUP_SOURCE_NAMES
