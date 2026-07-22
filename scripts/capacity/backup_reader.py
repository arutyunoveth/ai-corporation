from __future__ import annotations

import json
import os


_BACKUP_COMPONENTS = frozenset({
    "manifest.json",
    "database.dump",
    "artifacts.tar.gz",
    "SHA256SUMS",
})


def analyze_backup(
    backup_dir: str,
    live_artifacts_bytes: int | None = None,
) -> dict:
    result: dict = {
        "available": False,
        "error": None,
        "warnings": [],
        "backup_dir": None,
        "components": {},
        "compression_ratio": None,
        "total_bytes": None,
        "total_gib": None,
    }
    bdir = os.path.abspath(backup_dir)
    if not os.path.isdir(bdir):
        result["error"] = f"backup directory does not exist: {backup_dir}"
        result["warnings"].append("backup directory not accessible")
        return result

    result["available"] = True
    result["backup_dir"] = _path_id_short(bdir)
    found = set()
    for fname in os.listdir(bdir):
        fpath = os.path.join(bdir, fname)
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
                    result["warnings"].append(f"cannot parse manifest.json: {exc}")
            result["components"][fname] = entry

    for required in sorted(_BACKUP_COMPONENTS):
        if required not in found:
            result["components"][required] = {
                "file_name": required,
                "byte_size": None,
                "exists": False,
            }
            result["warnings"].append(f"missing backup component: {required}")

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
    if art_bytes is not None and art_bytes > 0 and live_artifacts_bytes is not None and live_artifacts_bytes > 0:
        ratio = art_bytes / live_artifacts_bytes
        result["compression_ratio"] = round(ratio, 4)
        result["warnings"].append(
            "compression ratio is based on a single snapshot and may not generalize"
        )
    return result


def _path_id_short(abs_path: str) -> str:
    import hashlib
    return hashlib.sha256(abs_path.encode("utf-8")).hexdigest()[:16]


def _safe_manifest(manifest: dict) -> dict:
    safe_keys = {
        "schema_version", "generated_at", "backup_version", "database_name",
        "tables_count", "total_size_bytes", "file_count", "artifact_count",
        "compression", "notes",
    }
    return {k: v for k, v in manifest.items() if k in safe_keys}
