from __future__ import annotations

from src.shared.config.settings import get_settings
from src.shared.db.base import Base
from src.tender_research.cli import main
from sqlalchemy import create_engine


def test_tender_research_check_db_cli_sqlite(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "check-db.sqlite"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    monkeypatch.setenv("AI_CORP_DATABASE_URL", db_url)
    get_settings.cache_clear()
    monkeypatch.setattr("sys.argv", ["tender-research", "check-db"])

    main()
    out = capsys.readouterr().out

    assert "database_dialect: sqlite" in out
    assert "database_url_masked: sqlite:///" in out
    assert "can_connect: True" in out
    assert "migration_head:" in out
    assert "pgvector_extension_available: False" in out
    assert "tables_count:" in out
