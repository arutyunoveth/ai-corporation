#!/usr/bin/env python3
"""Import a local vendor list into Supplier Registry."""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.modules.supplier_registry.vendor_import import (
    build_vendor_import_report_markdown,
    import_vendor_list,
)
from src.shared.config.settings import get_settings
from src.shared.db.base import Base
from src.shared.db import models as _db_models  # noqa: F401


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a vendor list into Supplier Registry.")
    parser.add_argument("--operator-id", required=True, help="Operator identifier, for example tender_operator_001")
    parser.add_argument("--file", required=True, type=Path, help="Path to vendor list file (.xlsx or .csv)")
    parser.add_argument("--source-label", required=True, help="Human-readable source label for the import batch")
    args = parser.parse_args()

    settings = get_settings()
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)

    file_path = args.file.resolve()
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_dir = Path("local_pilot_runs") / args.operator_id / "vendor_imports" / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    with Session(engine) as session:
        summary = import_vendor_list(
            session,
            operator_id=args.operator_id,
            file_path=file_path,
            source_label=args.source_label,
        )

    summary_path = output_dir / "vendor_import_summary.json"
    report_path = output_dir / "vendor_import_report.md"
    summary_path.write_text(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(build_vendor_import_report_markdown(summary), encoding="utf-8")

    print("=== Vendor List Import Complete ===")
    print(f"  Source file:   {file_path}")
    print(f"  Source label:  {args.source_label}")
    print(f"  Output dir:    {output_dir.resolve()}")
    print(f"  Summary:       {summary_path.resolve()}")
    print(f"  Report:        {report_path.resolve()}")
    print(f"  Created:       {summary.created_suppliers}")
    print(f"  Updated:       {summary.updated_suppliers}")
    print(f"  Skipped:       {summary.skipped_rows}")


if __name__ == "__main__":
    main()
