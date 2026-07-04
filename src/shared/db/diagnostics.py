from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import SQLAlchemyError


def masked_database_url(url: str) -> str:
    return make_url(url).render_as_string(hide_password=True)


def get_database_diagnostics(engine: Engine, *, alembic_ini_path: str = "alembic.ini") -> dict:
    info = {
        "database_dialect": engine.dialect.name,
        "database_url_masked": masked_database_url(str(engine.url)),
        "can_connect": False,
        "current_migration": None,
        "migration_head": None,
        "pgvector_extension_available": False,
        "tables_count": 0,
    }

    alembic_cfg = Config(alembic_ini_path)
    script = ScriptDirectory.from_config(alembic_cfg)
    try:
        info["migration_head"] = script.get_current_head()
    except Exception:
        info["migration_head"] = None

    try:
        with engine.connect() as connection:
            info["can_connect"] = True
            inspector = inspect(connection)
            info["tables_count"] = len(inspector.get_table_names())
            if "alembic_version" in inspector.get_table_names():
                rows = connection.execute(text("SELECT version_num FROM alembic_version")).fetchall()
                if rows:
                    revisions = [row[0] for row in rows]
                    info["current_migration"] = revisions[0] if len(revisions) == 1 else revisions
            if engine.dialect.name == "postgresql":
                info["pgvector_extension_available"] = bool(
                    connection.execute(
                        text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
                    ).scalar()
                )
    except SQLAlchemyError as exc:
        info["error"] = str(exc)
    return info
