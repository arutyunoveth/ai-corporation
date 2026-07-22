from __future__ import annotations

import hashlib
import os
import stat
from collections import defaultdict
from pathlib import Path


_TEMP_EXTENSIONS = frozenset({".tmp", ".partial", ".part"})


def _is_temp(name: str) -> bool:
    _, ext = os.path.splitext(name)
    return ext.lower() in _TEMP_EXTENSIONS


def _path_id(rel_path: str) -> str:
    return hashlib.sha256(rel_path.encode("utf-8")).hexdigest()


def collect_filesystem_metrics(
    roots: dict[str, str],
    include_relative_paths: bool = False,
) -> list[dict]:
    results: list[dict] = []
    for root_name, root_path_str in roots.items():
        info: dict = {
            "root_name": root_name,
            "available": False,
            "error": None,
            "warnings": [],
            "logical_bytes": None,
            "allocated_bytes": None,
            "files_count": 0,
            "directories_count": 0,
            "bytes_by_extension": {},
            "bytes_by_top_dir": {},
            "top_files": [],
            "temp_files_count": 0,
            "symlinks_count": 0,
        }
        root_path = Path(root_path_str)
        if not root_path.is_dir():
            info["available"] = False
            info["error"] = f"path does not exist or is not a directory: {root_path_str}"
            info["warnings"].append(f"root {root_name}: not accessible")
            results.append(info)
            continue

        info["available"] = True
        logical_total = 0
        allocated_total = 0
        ext_bytes: dict[str, int] = defaultdict(int)
        top_dir_bytes: dict[str, int] = defaultdict(int)
        top_files: list[dict] = []
        temp_count = 0
        symlink_count = 0
        file_count = 0
        dir_count = 0

        try:
            st = os.stat(root_path_str)
            if hasattr(st, "st_blocks"):
                info["allocated_bytes"] = st.st_blocks * 512
        except OSError:
            pass

        for dirpath, dirnames, filenames in os.walk(root_path_str, followlinks=False):
            dir_count += len(dirnames)
            for fn in filenames:
                fpath = os.path.join(dirpath, fn)
                try:
                    st_mode = os.lstat(fpath).st_mode
                    if stat.S_ISLNK(st_mode):
                        symlink_count += 1
                        continue
                    fst = os.stat(fpath)
                    if not stat.S_ISREG(fst.st_mode):
                        continue
                    size = fst.st_size
                    logical_total += size
                    if hasattr(fst, "st_blocks"):
                        allocated_total += fst.st_blocks * 512
                    file_count += 1
                    _, ext = os.path.splitext(fn)
                    ext_lower = ext.lower()
                    ext_bytes[ext_lower] += size
                    rel = os.path.relpath(fpath, root_path_str)
                    if _is_temp(fn):
                        temp_count += 1
                    parent = rel.split(os.sep)[0] if os.sep in rel else "."
                    top_dir_bytes[parent] += size

                    top_entry = {
                        "path_id": _path_id(rel),
                        "extension": ext_lower,
                        "byte_size": size,
                    }
                    if include_relative_paths:
                        top_entry["relative_path"] = rel
                    top_files.append(top_entry)
                except (OSError, PermissionError) as exc:
                    info["warnings"].append(f"cannot stat {fn}: {exc}")

        top_files.sort(key=lambda x: x["byte_size"], reverse=True)
        info["logical_bytes"] = logical_total
        info["allocated_bytes"] = allocated_total
        info["files_count"] = file_count
        info["directories_count"] = dir_count
        info["bytes_by_extension"] = dict(
            sorted(ext_bytes.items(), key=lambda x: x[1], reverse=True)
        )
        info["bytes_by_top_dir"] = dict(
            sorted(top_dir_bytes.items(), key=lambda x: x[1], reverse=True)
        )
        info["top_files"] = top_files[:20]
        info["temp_files_count"] = temp_count
        info["symlinks_count"] = symlink_count
        results.append(info)
    return results
