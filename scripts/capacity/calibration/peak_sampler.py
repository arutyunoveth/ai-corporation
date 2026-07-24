"""
Sample filesystem peak logical/allocated bytes during an operation.

Usage:
    # Background sampling (SIGINT/SIGTERM captures final sample)
    python scripts/capacity/calibration/peak_sampler.py \\
        --root data=/tmp/arvectum-arv009-b22b/data \\
        --interval-seconds 5 \\
        --output /tmp/peak-data.json
"""

import argparse
import json
import os
import signal
import stat
import sys
import time


def _real_path(path):
    st = os.lstat(path)
    if stat.S_ISLNK(st.st_mode):
        raise ValueError(f"Root path is a symlink: {path}")
    return os.path.realpath(path)


def _collect(root, follow_symlinks=False):
    logical = 0
    allocated = 0
    has_allocated = False
    try:
        for dirpath, dirnames, filenames in os.walk(root, followlinks=follow_symlinks):
            dirnames[:] = [
                d
                for d in dirnames
                if not os.path.islink(os.path.join(dirpath, d))
            ]
            for fn in filenames:
                fp = os.path.join(dirpath, fn)
                try:
                    if os.path.islink(fp):
                        continue
                    st = os.lstat(fp)
                    logical += st.st_size
                    try:
                        allocated += st.st_blocks * 512
                        has_allocated = True
                    except AttributeError:
                        pass
                except (OSError, ValueError):
                    continue
    except (OSError, ValueError):
        pass
    if not has_allocated:
        allocated = None
    return logical, allocated


def _sanitize(output, roots):
    sanitized = json.loads(json.dumps(output))
    for entry in sanitized.get("samples", []):
        if "root_path" in entry and isinstance(entry["root_path"], str):
            entry["root_path"] = _name_for(entry["root_path"], roots)
    if "baseline" in sanitized and isinstance(sanitized["baseline"], dict):
        for name in list(sanitized["baseline"].keys()):
            bl = sanitized["baseline"][name]
            if isinstance(bl, dict) and "path" in bl:
                bl["path"] = name
    if "roots" in sanitized and isinstance(sanitized["roots"], dict):
        sanitized["roots"] = {k: k for k in sanitized["roots"]}
    return sanitized


def _name_for(abspath, roots):
    for name, root_path in roots.items():
        if abspath.startswith(root_path.rstrip("/") + "/") or abspath == root_path:
            rel = os.path.relpath(abspath, root_path)
            if rel == ".":
                return name
            return f"{name}/{rel}"
    return "<unknown>"


def sample(roots, interval, output_path):
    roots_resolved = {}
    for name, path in roots.items():
        roots_resolved[name] = _real_path(path)

    baseline = {}
    for name, rp in roots_resolved.items():
        logical, allocated = _collect(rp)
        baseline[name] = {
            "path": rp,
            "logical_bytes": logical,
            "allocated_bytes": allocated,
        }

    samples = []
    peak_logical = {name: bl["logical_bytes"] for name, bl in baseline.items()}
    peak_allocated = {name: bl["allocated_bytes"] for name, bl in baseline.items()}

    running = True
    signal_received = None

    def _stop(signum, frame):
        nonlocal running, signal_received
        signal_received = signum
        running = False

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    start = time.monotonic()

    while True:
        t = time.monotonic() - start
        sample_entry = {"elapsed_seconds": round(t, 2)}
        for name, rp in roots_resolved.items():
            logical, allocated = _collect(rp)
            peak_logical[name] = max(peak_logical[name], logical)
            if allocated is not None and peak_allocated.get(name) is not None:
                peak_allocated[name] = max(peak_allocated[name], allocated)
            entry = {"logical_bytes": logical, "allocated_bytes": allocated}
            if t < 0.01:
                entry["status"] = "baseline"
            sample_entry[name] = entry
        samples.append(sample_entry)

        if not running:
            break

        deadline = time.monotonic() + interval
        while time.monotonic() < deadline and running:
            time.sleep(0.1)

    end = time.monotonic() - start

    if signal_received is not None:
        t = time.monotonic() - start
        final_entry = {"elapsed_seconds": round(t, 2), "status": "final"}
        for name, rp in roots_resolved.items():
            logical, allocated = _collect(rp)
            peak_logical[name] = max(peak_logical[name], logical)
            if allocated is not None and peak_allocated.get(name) is not None:
                peak_allocated[name] = max(peak_allocated[name], allocated)
            final_entry[name] = {
                "logical_bytes": logical,
                "allocated_bytes": allocated,
            }
        samples.append(final_entry)

    peak_deltas = {}
    for name in roots_resolved:
        bl = baseline[name]["logical_bytes"]
        pl = peak_logical[name]
        delta_logical = pl - bl if pl >= bl else 0
        bl_a = baseline[name]["allocated_bytes"]
        pl_a = peak_allocated[name]
        delta_alloc = (pl_a - bl_a) if (pl_a is not None and bl_a is not None and pl_a >= bl_a) else None
        peak_deltas[name] = {
            "baseline_logical_bytes": bl,
            "peak_logical_bytes": pl,
            "peak_delta_logical_bytes": delta_logical,
            "baseline_allocated_bytes": bl_a,
            "peak_allocated_bytes": pl_a,
            "peak_delta_allocated_bytes": delta_alloc,
        }

    output = {
        "tool": "peak_sampler",
        "schema_version": "1.0",
        "interval_seconds": interval,
        "total_elapsed_seconds": round(end, 2),
        "sample_count": len(samples),
        "roots": {name: rp for name, rp in roots_resolved.items()},
        "baseline": baseline,
        "peak_deltas": peak_deltas,
        "samples": samples,
        "signal": signal_received,
        "limitations": [],
    }

    if end < interval:
        output["limitations"].append(
            "Operation completed before one sampling interval. "
            "Peak delta reflects before/after comparison, not intermediate peak."
        )

    sanitized = _sanitize(output, roots)

    out_str = json.dumps(sanitized, indent=2, sort_keys=True, ensure_ascii=False)
    with open(output_path, "w") as f:
        f.write(out_str)
    print(f"Peak samples written: {output_path}", file=sys.stderr)
    return sanitized


def main():
    parser = argparse.ArgumentParser(description="Peak filesystem sampler")
    parser.add_argument(
        "--root",
        action="append",
        metavar="name=path",
        help="Root directory to monitor (repeatable, e.g. --root data=/path)",
    )
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=5.0,
        help="Sampling interval in seconds (minimum 2.0)",
    )
    parser.add_argument("--output", required=True, help="Output JSON path")
    args = parser.parse_args()

    if args.interval_seconds < 2.0:
        print("error: --interval-seconds must be >= 2.0", file=sys.stderr)
        sys.exit(1)

    if not args.root:
        print("error: at least one --root required", file=sys.stderr)
        sys.exit(1)

    roots = {}
    for r in args.root:
        if "=" not in r:
            print(f"error: --root must be name=path, got: {r}", file=sys.stderr)
            sys.exit(1)
        name, path = r.split("=", 1)
        if not os.path.exists(path):
            print(f"error: root path does not exist: {path}", file=sys.stderr)
            sys.exit(1)
        roots[name.strip()] = path.strip()

    sample(roots, args.interval_seconds, args.output)


if __name__ == "__main__":
    main()
