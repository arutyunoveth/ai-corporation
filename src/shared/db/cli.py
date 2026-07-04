from __future__ import annotations

import argparse

from sqlalchemy import create_engine

from src.shared.config.settings import get_settings
from src.shared.db.diagnostics import get_database_diagnostics


def cmd_check_db() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url, future=True)
    info = get_database_diagnostics(engine)
    for key in (
        "database_dialect",
        "database_url_masked",
        "can_connect",
        "current_migration",
        "migration_head",
        "pgvector_extension_available",
        "tables_count",
    ):
        print(f"{key}: {info.get(key)}")
    if info.get("error"):
        print(f"error: {info['error']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Shared DB CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check-db", help="Show database dialect, connectivity, migration state, and pgvector status")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "check-db":
        cmd_check_db()


if __name__ == "__main__":
    main()
