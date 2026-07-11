from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.shared.db.base import Base
from src.tender_research.config import TenderResearchConfig
from src.tender_research.eis_loader import EisTenderLoader
from src.tender_research.pipeline import TenderResearchPipeline
from src.tender_research.repository import TenderRepository


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_pipeline_smoke():
    session = _session()
    config = TenderResearchConfig(
        enabled=True,
        data_dir="/tmp/tender_research_test",
        web_search_enabled=False,
        web_fetch_enabled=False,
    )
    pipeline = TenderResearchPipeline(session, config=config)
    count = pipeline.ingest_eis_tenders(limit=2)
    assert count == 2
    repo = TenderRepository(session)
    assert repo.count_tenders() == 2
    assert repo.count_customers() >= 1

    # Build queries
    tenders = repo.list_tenders(limit=1)
    assert len(tenders) == 1
    qcount = pipeline.build_search_queries(tenders[0].id)
    assert qcount > 0
    assert repo.count_search_queries() >= qcount
