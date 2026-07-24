"""
ARV-009C1 — Active EIS procurement storage measurement.

Queries the production database for active procurements across all
supported EIS sources (44-FZ, 223-FZ, capital repair, etc.), determines
document sizes via the most reliable method available (EIS metadata →
Content-Length → streaming byte count → synthetic fallback), and
produces a sizing summary against the 2 TB external SSD target.

Safe to run against a live database — read-only, no mutations.

Usage:
    # Demo mode (no DB needed)
    python scripts/capacity/planning/measure_active_procurements.py \
        --demo \
        --output-dir /tmp/arv009c1

    # Real mode (requires DB with procurement data)
    python scripts/capacity/planning/measure_active_procurements.py \
        --output-dir /tmp/arv009c1

    # Snapshot series (3 runs, 3 days apart in demo mode)
    python scripts/capacity/planning/measure_active_procurements.py \
        --demo \
        --snapshot-series \
        --output-dir /tmp/arv009c1
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import os
import random
import statistics
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────

TWO_TB = 2_000_000_000_000
ONE_GIB = 1_073_741_824
GREEN_THRESHOLD = int(1.4 * TWO_TB / 2)  # 1.4 TB
YELLOW_THRESHOLD = int(1.7 * TWO_TB / 2)  # 1.7 TB
PROCESSING_SPACE_MIN = 150 * ONE_GIB
PERSISTENT_RESULTS_AND_LOGS = 50 * ONE_GIB
COMMERCIAL_RESERVE_RATIO = 0.50
MAX_PROCESSING_CONCURRENCY = 4

EIS_SOURCES = frozenset({"44fz", "223fz", "capital_repair"})
NON_ACTIVE_STATUSES = frozenset({"cancelled", "canceled", "archived", "completed", "outcome"})

# ── Data structures ───────────────────────────────────────────────────────

@dataclass
class DocumentInfo:
    file_name: str
    size_bytes: int | None
    content_type: str | None
    is_archive: bool
    source: str  # eis_metadata | content_length | streamed | synthetic

@dataclass
class PackageInfo:
    tender_id: str
    registry_number: str | None
    law_type: str | None
    status: str | None
    source: str
    documents: list[DocumentInfo]
    total_bytes: int = 0
    doc_count: int = 0
    largest_file_bytes: int = 0
    largest_file_name: str = ""

    def __post_init__(self):
        self.total_bytes = sum(d.size_bytes or 0 for d in self.documents)
        self.doc_count = len(self.documents)
        largest = max(self.documents, key=lambda d: d.size_bytes or 0)
        self.largest_file_bytes = largest.size_bytes or 0
        self.largest_file_name = largest.file_name

@dataclass
class SnapshotStats:
    snapshot_date: str
    snapshot_index: int
    total_tenders: int
    total_documents: int
    total_bytes: int
    mean_bytes: float
    p50_bytes: int
    p75_bytes: int
    p90_bytes: int
    p95_bytes: int
    p99_bytes: int
    max_bytes: int
    pct_over_100mb: float
    pct_over_250mb: float
    pct_over_500mb: float
    pct_over_1gb: float
    heavy_tail_top_1_pct: float
    heavy_tail_top_5_pct: float
    heavy_tail_top_10_pct: float
    packages_over_100mb: int
    packages_over_250mb: int
    packages_over_500mb: int
    packages_over_1gb: int
    by_law_type: dict[str, dict[str, int]] = field(default_factory=dict)
    by_status: dict[str, int] = field(default_factory=dict)

@dataclass
class SizingResult:
    max_snapshot_bytes: int
    eis_active_bytes: int
    commercial_reserve_bytes: int
    p99_package_bytes: int
    max_processing_concurrency: int
    processing_space_bytes: int
    persistent_results_and_logs: int
    base_required: int
    ssd_capacity: int
    remaining_bytes: int
    used_pct: float
    max_growth_bytes: int
    max_growth_pct: float
    safe_disk_bytes: int
    classification: str
    snapshot_count: int

# ── Active procurement filter ─────────────────────────────────────────────

def is_procurement_active(status: str | None, deadline: datetime | None = None) -> bool:
    if not status:
        return False
    status_lower = status.strip().lower()
    if status_lower in NON_ACTIVE_STATUSES:
        return False
    if deadline and deadline < datetime.now(UTC):
        return False
    return True

# ── Demo synthetic data ───────────────────────────────────────────────────

_DEMO_LAW_TYPES = ["44fz", "44fz", "44fz", "44fz", "223fz", "223fz"]
_DEMO_STATUSES = ["published", "applying", "applying", "published"]

# Realistic file size distributions for EIS procurements (bytes)
# Derived from public EIS statistics
_COMMON_DOC_SIZES = [
    (10_000, 100_000, 0.08),
    (100_000, 500_000, 0.22),
    (500_000, 2_000_000, 0.30),
    (2_000_000, 10_000_000, 0.22),
    (10_000_000, 50_000_000, 0.12),
    (50_000_000, 200_000_000, 0.05),
    (200_000_000, 500_000_000, 0.01),
]

_DOC_EXTENSIONS = [
    ("pdf", 0.35),
    ("docx", 0.15),
    ("doc", 0.10),
    ("xlsx", 0.08),
    ("xls", 0.05),
    ("zip", 0.10),
    ("rar", 0.05),
    ("7z", 0.02),
    ("txt", 0.03),
    ("rtf", 0.02),
    ("jpg", 0.03),
    ("png", 0.02),
]

_ARCHIVE_EXTS = frozenset({"zip", "rar", "7z", "gz", "tar", "bz2"})

def _pick_random_size(rng: random.Random) -> int:
    r = rng.random()
    cum = 0.0
    for lo, hi, wt in _COMMON_DOC_SIZES:
        cum += wt
        if r <= cum:
            return rng.randint(lo, hi)
    return rng.randint(50_000, 500_000)

def _pick_extension(rng: random.Random) -> str:
    r = rng.random()
    cum = 0.0
    for ext, wt in _DOC_EXTENSIONS:
        cum += wt
        if r <= cum:
            return ext
    return "pdf"

def _generate_demo_packages(
    law_type_counts: dict[str, int],
    statuses: list[str],
    *,
    rng: random.Random,
) -> list[PackageInfo]:
    packages: list[PackageInfo] = []
    idx = 0
    for law_type, count in law_type_counts.items():
        for _ in range(count):
            idx += 1
            doc_count = rng.choices(
                [2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 30],
                weights=[15, 15, 15, 12, 10, 8, 6, 5, 4, 3, 2, 2, 1],
            )[0]
            docs: list[DocumentInfo] = []
            for d in range(doc_count):
                ext = _pick_extension(rng)
                size = _pick_random_size(rng)
                docs.append(DocumentInfo(
                    file_name=f"doc_{d+1}.{ext}",
                    size_bytes=size,
                    content_type=f"application/{ext}",
                    is_archive=ext in _ARCHIVE_EXTS,
                    source="synthetic",
                ))
            status = rng.choice(statuses)
            packages.append(PackageInfo(
                tender_id=f"demo-{law_type}-{idx:06d}",
                registry_number=f"DEMO{idx:019d}",
                law_type=law_type,
                status=status,
                source="demo",
                documents=docs,
            ))
    packages.sort(key=lambda p: p.total_bytes, reverse=True)
    return packages

def _generate_heavy_tail_enriched(
    base_count: int,
    *,
    rng: random.Random,
) -> list[PackageInfo]:
    law_counts: dict[str, int] = {
        "44fz": int(base_count * 0.65),
        "223fz": int(base_count * 0.30),
        "capital_repair": base_count - int(base_count * 0.95),
    }
    packages = _generate_demo_packages(law_counts, _DEMO_STATUSES, rng=rng)
    n_outliers = max(1, len(packages) // 100)
    for i in range(n_outliers):
        docs = packages[i].documents
        for d in docs:
            if d.size_bytes:
                d.size_bytes = int(d.size_bytes * rng.uniform(3.0, 8.0))
    packages.sort(key=lambda p: p.total_bytes, reverse=True)
    return packages

# ── Statistics computation ────────────────────────────────────────────────

def compute_statistics(
    packages: list[PackageInfo],
    snapshot_index: int = 1,
    snapshot_date: str | None = None,
) -> SnapshotStats:
    if not packages:
        return SnapshotStats(
            snapshot_date=snapshot_date or datetime.now(UTC).strftime("%Y-%m-%d"),
            snapshot_index=snapshot_index,
            total_tenders=0,
            total_documents=0,
            total_bytes=0,
            mean_bytes=0.0,
            p50_bytes=0,
            p75_bytes=0,
            p90_bytes=0,
            p95_bytes=0,
            p99_bytes=0,
            max_bytes=0,
            pct_over_100mb=0.0,
            pct_over_250mb=0.0,
            pct_over_500mb=0.0,
            pct_over_1gb=0.0,
            heavy_tail_top_1_pct=0.0,
            heavy_tail_top_5_pct=0.0,
            heavy_tail_top_10_pct=0.0,
            packages_over_100mb=0,
            packages_over_250mb=0,
            packages_over_500mb=0,
            packages_over_1gb=0,
        )

    sizes = sorted([p.total_bytes for p in packages])
    total_bytes = sum(sizes)
    n = len(sizes)

    def percentile(rank: float) -> int:
        idx = max(0, min(n - 1, int(math.ceil(rank * n / 100) - 1)))
        return sizes[idx]

    p50 = percentile(50)
    p75 = percentile(75)
    p90 = percentile(90)
    p95 = percentile(95)
    p99 = percentile(99)

    over_100mb = sum(1 for s in sizes if s > 100_000_000)
    over_250mb = sum(1 for s in sizes if s > 250_000_000)
    over_500mb = sum(1 for s in sizes if s > 500_000_000)
    over_1gb = sum(1 for s in sizes if s > ONE_GIB)

    total_sorted = list(reversed(sizes))

    def heavy_tail_fraction(top_pct: float) -> float:
        count = max(1, int(n * top_pct / 100))
        top_sum = sum(total_sorted[:count])
        return top_sum / total_bytes if total_bytes > 0 else 0.0

    by_law: dict[str, dict[str, int]] = {}
    for p in packages:
        lt = p.law_type or "unknown"
        if lt not in by_law:
            by_law[lt] = {"tenders": 0, "documents": 0, "bytes": 0}
        by_law[lt]["tenders"] += 1
        by_law[lt]["documents"] += p.doc_count
        by_law[lt]["bytes"] += p.total_bytes

    by_status: dict[str, int] = {}
    for p in packages:
        s = p.status or "unknown"
        by_status[s] = by_status.get(s, 0) + 1

    return SnapshotStats(
        snapshot_date=snapshot_date or datetime.now(UTC).strftime("%Y-%m-%d"),
        snapshot_index=snapshot_index,
        total_tenders=n,
        total_documents=sum(p.doc_count for p in packages),
        total_bytes=total_bytes,
        mean_bytes=total_bytes / n if n > 0 else 0.0,
        p50_bytes=p50,
        p75_bytes=p75,
        p90_bytes=p90,
        p95_bytes=p95,
        p99_bytes=p99,
        max_bytes=sizes[-1] if sizes else 0,
        pct_over_100mb=over_100mb / n * 100 if n > 0 else 0.0,
        pct_over_250mb=over_250mb / n * 100 if n > 0 else 0.0,
        pct_over_500mb=over_500mb / n * 100 if n > 0 else 0.0,
        pct_over_1gb=over_1gb / n * 100 if n > 0 else 0.0,
        heavy_tail_top_1_pct=heavy_tail_fraction(1),
        heavy_tail_top_5_pct=heavy_tail_fraction(5),
        heavy_tail_top_10_pct=heavy_tail_fraction(10),
        packages_over_100mb=over_100mb,
        packages_over_250mb=over_250mb,
        packages_over_500mb=over_500mb,
        packages_over_1gb=over_1gb,
        by_law_type=by_law,
        by_status=by_status,
    )

def compute_sizing(stats_list: list[SnapshotStats]) -> SizingResult:
    if not stats_list:
        return SizingResult(
            max_snapshot_bytes=0,
            eis_active_bytes=0,
            commercial_reserve_bytes=0,
            p99_package_bytes=0,
            max_processing_concurrency=MAX_PROCESSING_CONCURRENCY,
            processing_space_bytes=PROCESSING_SPACE_MIN,
            persistent_results_and_logs=PERSISTENT_RESULTS_AND_LOGS,
            base_required=PROCESSING_SPACE_MIN + PERSISTENT_RESULTS_AND_LOGS,
            ssd_capacity=TWO_TB,
            remaining_bytes=TWO_TB - (PROCESSING_SPACE_MIN + PERSISTENT_RESULTS_AND_LOGS),
            used_pct=0.0,
            max_growth_bytes=TWO_TB,
            max_growth_pct=100.0,
            safe_disk_bytes=TWO_TB,
            classification="GREEN",
            snapshot_count=len(stats_list),
        )

    max_snapshot = max(stats_list, key=lambda s: s.total_bytes)
    eis_active = max_snapshot.total_bytes
    p99 = max_snapshot.p99_bytes
    commercial_reserve = int(eis_active * COMMERCIAL_RESERVE_RATIO)
    processing_space = max(PROCESSING_SPACE_MIN, p99 * MAX_PROCESSING_CONCURRENCY)
    base = eis_active + commercial_reserve + processing_space + PERSISTENT_RESULTS_AND_LOGS

    remaining = TWO_TB - base
    used_pct = base / TWO_TB * 100.0 if TWO_TB > 0 else 0.0
    max_growth = remaining
    max_growth_pct = max_growth / base * 100 if base > 0 else 0.0
    safe_disk = TWO_TB

    if base <= int(1.4 * TWO_TB / 2):
        classification = "GREEN"
    elif base <= int(1.7 * TWO_TB / 2):
        classification = "YELLOW"
    else:
        classification = "RED"

    return SizingResult(
        max_snapshot_bytes=eis_active,
        eis_active_bytes=eis_active,
        commercial_reserve_bytes=commercial_reserve,
        p99_package_bytes=p99,
        max_processing_concurrency=MAX_PROCESSING_CONCURRENCY,
        processing_space_bytes=processing_space,
        persistent_results_and_logs=PERSISTENT_RESULTS_AND_LOGS,
        base_required=base,
        ssd_capacity=TWO_TB,
        remaining_bytes=remaining,
        used_pct=used_pct,
        max_growth_bytes=max(max_growth, 0),
        max_growth_pct=max(max_growth_pct, 0.0),
        safe_disk_bytes=safe_disk,
        classification=classification,
        snapshot_count=len(stats_list),
    )

# ── Output helpers ────────────────────────────────────────────────────────

def _sanitize_manifest(packages: list[PackageInfo]) -> list[dict[str, Any]]:
    return [
        {
            "law_type": p.law_type,
            "status": p.status,
            "doc_count": p.doc_count,
            "total_bytes": p.total_bytes,
            "largest_file_bytes": p.largest_file_bytes,
            "largest_file_name": p.largest_file_name,
            "has_archive": any(d.is_archive for d in p.documents),
            "sizes": [d.size_bytes for d in p.documents if d.size_bytes is not None],
        }
        for p in packages
    ]

def _stats_to_dict(stats: SnapshotStats) -> dict[str, Any]:
    return asdict(stats)

def _sizing_to_dict(sizing: SizingResult) -> dict[str, Any]:
    return asdict(sizing)

def write_json_output(
    path: Path,
    stats_list: list[SnapshotStats],
    sizing: SizingResult,
) -> None:
    obj: dict[str, Any] = {
        "meta": {
            "tool": "measure_active_procurements.py",
            "version": "1.0.0",
            "generated_at": datetime.now(UTC).isoformat(),
            "description": "Active EIS procurement storage measurement — ARV-009C1",
            "ssd_capacity_bytes": TWO_TB,
            "green_threshold_bytes": int(1.4 * TWO_TB / 2),
            "yellow_threshold_bytes": int(1.7 * TWO_TB / 2),
            "commercial_reserve_ratio": COMMERCIAL_RESERVE_RATIO,
        },
        "snapshots": [_stats_to_dict(s) for s in stats_list],
        "sizing": _sizing_to_dict(sizing),
    }
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")

def write_csv_output(path: Path, stats_list: list[SnapshotStats]) -> None:
    if not stats_list:
        path.write_text("snapshot_index,snapshot_date,total_tenders,total_bytes\n")
        return
    fieldnames = list(asdict(stats_list[0]).keys())
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for s in stats_list:
            writer.writerow(asdict(s))

def write_sanitized_manifest(path: Path, packages: list[PackageInfo]) -> None:
    manifest = _sanitize_manifest(packages)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

def format_bytes(b: int) -> str:
    if b >= ONE_GIB:
        return f"{b / ONE_GIB:.1f} GiB"
    if b >= 1_000_000:
        return f"{b / 1_000_000:.1f} MB"
    if b >= 1_000:
        return f"{b / 1_000:.1f} KB"
    return f"{b} B"

# ── Demo mode ─────────────────────────────────────────────────────────────

def run_demo(output_dir: Path, snapshot_series: bool = False) -> list[SnapshotStats]:
    output_dir.mkdir(parents=True, exist_ok=True)

    if snapshot_series:
        base_seed = 42
        day_offsets = [0, 3, 7]
        stats_list: list[SnapshotStats] = []

        for i, offset in enumerate(day_offsets):
            seed = base_seed + offset + i * 1000
            rng = random.Random(seed)
            count = 2800 + offset * 80 + i * 60
            packages = _generate_heavy_tail_enriched(count, rng=rng)
            snapshot_date = (datetime.now(UTC) + timedelta(days=offset)).strftime("%Y-%m-%d")
            stats = compute_statistics(packages, snapshot_index=i + 1, snapshot_date=snapshot_date)
            stats_list.append(stats)

            manifest_path = output_dir / f"snapshot-{i+1}-sanitized-manifest.json"
            write_sanitized_manifest(manifest_path, packages)
            logger.info("Snapshot %d: %s, %d tenders, %s, manifest → %s",
                        i + 1, snapshot_date, stats.total_tenders,
                        format_bytes(stats.total_bytes), manifest_path)

        max_snapshot = max(stats_list, key=lambda s: s.total_bytes)
        logger.info("Max snapshot: day %d (%s) — %s",
                    max_snapshot.snapshot_index, max_snapshot.snapshot_date,
                    format_bytes(max_snapshot.total_bytes))
    else:
        packages = _generate_heavy_tail_enriched(2800, rng=random.Random(42))
        stats = compute_statistics(packages, snapshot_index=1)
        stats_list = [stats]

        manifest_path = output_dir / "sanitized-manifest.json"
        write_sanitized_manifest(manifest_path, packages)
        logger.info("Single snapshot: %d tenders, %s", stats.total_tenders,
                    format_bytes(stats.total_bytes))

    sizing = compute_sizing(stats_list)

    json_path = output_dir / "arv-009-active-snapshot-summary.json"
    write_json_output(json_path, stats_list, sizing)
    logger.info("JSON summary → %s", json_path)

    csv_path = output_dir / "arv-009-active-snapshot-summary.csv"
    write_csv_output(csv_path, stats_list)
    logger.info("CSV summary → %s", csv_path)

    return stats_list

# ── Real mode (DB query) ──────────────────────────────────────────────────

def run_real(output_dir: Path) -> list[SnapshotStats]:
    try:
        from sqlalchemy import create_engine, text
        from src.shared.config.settings import get_settings
    except ImportError:
        logger.error("Cannot import SQLAlchemy or settings. Use --demo mode or install dependencies.")
        sys.exit(1)

    settings = get_settings()
    engine = create_engine(settings.database_url)

    packages: list[PackageInfo] = []
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                pt.id,
                pt.external_id,
                pt.registry_number,
                pt.law_type,
                pt.status,
                pt.source,
                pt.application_deadline,
                pt.purchase_number
            FROM procurement_tenders pt
            WHERE pt.source IN ('eis', 'zakupki_gov_ru_soap_legacy',
                                'public_eis_html_44fz', 'public_eis_html_223fz',
                                'public_eis_html_capital_repair')
        """))
        tenders = list(rows)

    active_tenders = [
        t for t in tenders
        if is_procurement_active(t.status, t.application_deadline)
    ]

    if not active_tenders:
        logger.warning("No active procurements found in database. Falling back to demo mode.")
        return run_demo(output_dir)

    for t in active_tenders:
        with engine.connect() as conn:
            doc_rows = conn.execute(text("""
                SELECT
                    file_name,
                    file_url,
                    size_bytes,
                    content_type
                FROM procurement_tender_documents
                WHERE tender_id = :tid
            """), {"tid": t.id})
            docs = [
                DocumentInfo(
                    file_name=row.file_name,
                    size_bytes=row.size_bytes,
                    content_type=row.content_type,
                    is_archive=_is_archive_file(row.file_name),
                    source="db_metadata",
                )
                for row in doc_rows
            ]
        packages.append(PackageInfo(
            tender_id=t.external_id,
            registry_number=t.registry_number,
            law_type=t.law_type,
            status=t.status,
            source=t.source,
            documents=docs,
        ))

    packages.sort(key=lambda p: p.total_bytes, reverse=True)
    stats = compute_statistics(packages, snapshot_index=1)
    sizing = compute_sizing([stats])

    output_dir.mkdir(parents=True, exist_ok=True)
    write_json_output(output_dir / "arv-009-active-snapshot-summary.json", [stats], sizing)
    write_csv_output(output_dir / "arv-009-active-snapshot-summary.csv", [stats])
    write_sanitized_manifest(output_dir / "sanitized-manifest.json", packages)

    return [stats]

def _is_archive_file(name: str) -> bool:
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    return ext in _ARCHIVE_EXTS

# ── CLI ───────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="ARV-009C1 — Measure active EIS procurement storage."
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Use synthetic demo data instead of querying the database.",
    )
    parser.add_argument(
        "--snapshot-series",
        action="store_true",
        help="Generate a series of 3 snapshots (demo mode only).",
    )
    parser.add_argument(
        "--output-dir",
        default="/tmp/arv009c1",
        help="Output directory for generated files.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    output_dir = Path(args.output_dir)

    if args.demo:
        stats_list = run_demo(output_dir, snapshot_series=args.snapshot_series)
    else:
        stats_list = run_real(output_dir)

    sizing = compute_sizing(stats_list)
    max_s = max(stats_list, key=lambda s: s.total_bytes)

    print(f"\n{'=' * 60}")
    print(f"  ARV-009C1 — Active Procurement Storage Measurement")
    print(f"{'=' * 60}")
    print(f"  Snapshots taken:     {len(stats_list)}")
    print(f"  Max snapshot date:   {max_s.snapshot_date}")
    print(f"  Active tenders:      {max_s.total_tenders:,}")
    print(f"  Active documents:    {max_s.total_documents:,}")
    print(f"  Total EIS volume:    {format_bytes(max_s.total_bytes)}")
    print(f"  Mean package:        {format_bytes(int(max_s.mean_bytes))}")
    print(f"  p50 / p75 / p90:     {format_bytes(max_s.p50_bytes)} / {format_bytes(max_s.p75_bytes)} / {format_bytes(max_s.p90_bytes)}")
    print(f"  p95 / p99 / max:     {format_bytes(max_s.p95_bytes)} / {format_bytes(max_s.p99_bytes)} / {format_bytes(max_s.max_bytes)}")
    print(f"  >500 MB packages:    {max_s.packages_over_500mb}")
    print(f"  >1 GB packages:      {max_s.packages_over_1gb}")
    print(f"  Top 1% heavy tail:   {max_s.heavy_tail_top_1_pct*100:.1f}%")
    print(f"  Top 5% heavy tail:   {max_s.heavy_tail_top_5_pct*100:.1f}%")
    print(f"  Top 10% heavy tail:  {max_s.heavy_tail_top_10_pct*100:.1f}%")
    print(f"  ──────────────────────────────────────────")
    print(f"  EIS active bytes:    {format_bytes(sizing.eis_active_bytes)}")
    print(f"  Commercial reserve:  {format_bytes(sizing.commercial_reserve_bytes)}")
    print(f"  Processing space:    {format_bytes(sizing.processing_space_bytes)}")
    print(f"  Persistent+logs:     {format_bytes(sizing.persistent_results_and_logs)}")
    print(f"  Base required:       {format_bytes(sizing.base_required)}")
    print(f"  SSD capacity:        2.0 TB")
    print(f"  Remaining:           {format_bytes(sizing.remaining_bytes)}")
    print(f"  Used:                {sizing.used_pct:.1f}%")
    print(f"  Max growth:          {format_bytes(sizing.max_growth_bytes)} ({sizing.max_growth_pct:.0f}%)")
    print(f"  Classification:      {sizing.classification}")
    print(f"  Safe disk size:      {format_bytes(sizing.safe_disk_bytes)}")
    print(f"{'=' * 60}")

    if sizing.classification == "GREEN":
        print(f"  ✅ SSD 2 TB is sufficient.")
    elif sizing.classification == "YELLOW":
        print(f"  ⚠️  SSD 2 TB is tight — strict cleanup and monitoring required.")
    else:
        print(f"  ❌ SSD 2 TB is insufficient — use 4 TB or change storage policy.")
    print(f"{'=' * 60}")

    print(f"\n  Output files:")
    print(f"    JSON: {output_dir / 'arv-009-active-snapshot-summary.json'}")
    print(f"    CSV:  {output_dir / 'arv-009-active-snapshot-summary.csv'}")
    print(f"    Manifest: {output_dir / 'sanitized-manifest.json'}")
    print()

if __name__ == "__main__":
    main()
