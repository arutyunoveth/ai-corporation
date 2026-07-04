from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Load .env and .env.local early so ZakupkiSoapSettings (which reads os.environ)
# can find ZAKUPKI_GOV_RU_SOAP_TOKEN and other env vars.
_load_dotenv_result = load_dotenv(".env", override=False)
_load_dotenv_local_result = load_dotenv(".env.local", override=False)

from src.tender_research.config import load_config
from src.tender_research.pipeline import TenderResearchPipeline
from src.tender_research.repository import TenderRepository
from src.shared.config.settings import get_settings
from src.shared.db.base import Base

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("tender_research.cli")


def _get_session() -> Session:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    from sqlalchemy.orm import sessionmaker
    return sessionmaker(bind=engine)()


def cmd_check_eis_config(args: argparse.Namespace) -> None:
    config = load_config()
    print(f"eis_mode: {config.eis_mode}")
    print(f"eis_discovery_mode: {config.eis_discovery_mode}")
    if config.eis_mode != "real":
        print("(switching to real mode for diagnostics)")
    try:
        from src.tender_research.eis_real_loader import RealEisLoader
        loader = RealEisLoader()
        info = loader.check_config()
    except Exception as e:
        print(f"check_config error: {e}")
        return
    for k, v in info.items():
        if isinstance(v, list):
            print(f"  {k}: {', '.join(v)}")
        else:
            print(f"  {k}: {v}")
    print()
    print("dotenv loaded .env:", _load_dotenv_result)
    print("dotenv loaded .env.local:", _load_dotenv_local_result)


def cmd_stats(args: argparse.Namespace) -> None:
    session = _get_session()
    repo = TenderRepository(session)
    config = load_config()
    data_dir = Path(config.data_dir)
    data_size = 0
    if data_dir.exists():
        for f in data_dir.rglob("*"):
            if f.is_file():
                data_size += f.stat().st_size
    print(f"tenders_total: {repo.count_tenders()}")
    print(f"customers_total: {repo.count_customers()}")
    print(f"documents_total: {repo.count_documents()}")
    print(f"documents_downloaded: {repo.count_documents_by_status('downloaded')}")
    print(f"search_queries_total: {repo.count_search_queries()}")
    print(f"search_results_total: {repo.count_search_results()}")
    print(f"web_pages_fetched: {repo.count_web_pages_by_status('fetched')}")
    print(f"web_pages_failed: {repo.count_web_pages_by_status('failed')}")
    print(f"artifacts_total: {repo.count_artifacts()}")
    print(f"data_dir_size_mb: {data_size / 1024 / 1024:.1f}")


def _build_pipeline(args: argparse.Namespace) -> TenderResearchPipeline:
    config = load_config()
    if args.eis_mode:
        object.__setattr__(config, "eis_mode", args.eis_mode)
    session = _get_session()
    return TenderResearchPipeline(session, config=config)


def cmd_ingest_eis_registry_list(args: argparse.Namespace) -> None:
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Seed file not found: {file_path}")
        return
    numbers = [
        line.strip() for line in file_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not numbers:
        print("No registry numbers found in seed file.")
        return
    print(f"Loaded {len(numbers)} registry numbers from {file_path}")

    pipeline = _build_pipeline(args)
    result = pipeline.ingest_eis_by_registry_numbers(
        registry_numbers=numbers,
        limit=args.limit,
    )
    print(f"Registry ingest complete:")
    print(f"  total: {result['total']}")
    print(f"  saved: {result['saved']}")
    print(f"  skipped: {result['skipped']}")
    print(f"  no_data: {result['no_data']}")
    print(f"  connection_resets: {result['connection_resets']}")
    print(f"  missing_token: {result['missing_token']}")
    if result["errors"]:
        print(f"  errors ({len(result['errors'])}):")
        for e in result["errors"][:5]:
            print(f"    - {e}")


def cmd_ingest_eis(args: argparse.Namespace) -> None:
    pipeline = _build_pipeline(args)
    date_from = datetime.fromisoformat(args.date_from) if args.date_from else None
    date_to = datetime.fromisoformat(args.date_to) if args.date_to else None
    count = pipeline.ingest_eis_tenders(
        date_from=date_from,
        date_to=date_to,
        limit=args.limit,
        law_type=args.law_type,
        query=args.query,
    )
    print(f"Ingested {count} tenders from EIS.")


def cmd_research_batch(args: argparse.Namespace) -> None:
    pipeline = _build_pipeline(args)
    date_from = datetime.fromisoformat(args.date_from) if args.date_from else None
    date_to = datetime.fromisoformat(args.date_to) if args.date_to else None
    results = pipeline.run_batch(
        date_from=date_from,
        date_to=date_to,
        limit=args.limit,
        law_type=args.law_type,
        query=args.query,
        web_search=args.web_search,
    )
    ok = sum(1 for r in results if "error" not in r)
    failed = sum(1 for r in results if "error" in r)
    print(f"Batch complete: {ok} ok, {failed} failed")
    for r in results:
        status = "OK" if "error" not in r else f"FAIL: {r['error']}"
        title = r.get("title", r.get("external_id", "?"))
        print(f"  [{status}] {title}")


def cmd_research_one(args: argparse.Namespace) -> None:
    pipeline = _build_pipeline(args)
    repo = pipeline._repo
    tender = repo.get_tender_by_external("eis", args.external_id)
    if not tender:
        # Try to fetch from EIS first
        from src.tender_research.eis_loader import EisTenderLoader
        loader = EisTenderLoader()
        raw = loader.fetch_tender_details(args.external_id)
        if raw:
            count = pipeline.ingest_eis_tenders(query=raw.title, limit=1)
            if count:
                tender = repo.get_tender_by_external("eis", args.external_id)
        if not tender:
            print(f"Tender {args.external_id} not found")
            return
    result = pipeline.run_full(tender.id)
    print(f"Results for {args.external_id}:")
    for k, v in result.items():
        print(f"  {k}: {v}")


def cmd_build_queries(args: argparse.Namespace) -> None:
    session = _get_session()
    pipeline = TenderResearchPipeline(session)
    count = pipeline.build_search_queries(args.tender_id)
    print(f"Built {count} search queries for tender {args.tender_id}")


def cmd_web_search(args: argparse.Namespace) -> None:
    session = _get_session()
    pipeline = TenderResearchPipeline(session)
    count = pipeline.run_web_search(args.tender_id)
    print(f"Saved {count} search results for tender {args.tender_id}")


def cmd_fetch_pages(args: argparse.Namespace) -> None:
    session = _get_session()
    pipeline = TenderResearchPipeline(session)
    result = pipeline.fetch_search_results(args.tender_id, max_pages=args.limit)
    print(f"Fetched {result.get('fetched', 0)} pages, {result.get('failed', 0)} failed")


def cmd_discover_registry_numbers(args: argparse.Namespace) -> None:
    pipeline = _build_pipeline(args)
    result = pipeline.discover_registry_numbers(
        source=args.source,
        days_back=args.days_back,
        limit=args.limit,
        seed_file=args.seed_file,
    )
    print(f"selected_source: {result.selected_source}")
    print(f"is_demo: {result.is_demo}")
    if result.warnings:
        for w in result.warnings:
            print(f"  warning: {w}")
    print(f"Discovered {len(result.numbers)} registry numbers:")
    for rn in result.numbers:
        demo_tag = " [DEMO]" if rn.is_demo else ""
        print(f"  {rn.registry_number}{demo_tag}")

    if args.output and result.numbers:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"# discovered via {result.selected_source} (is_demo={result.is_demo})"]
        lines += [f"# {w}" for w in result.warnings]
        lines += [rn.registry_number for rn in result.numbers if not rn.is_demo]
        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Saved {len(lines) - len(result.warnings) - 1} numbers to {output_path}")


def cmd_research_discovered(args: argparse.Namespace) -> None:
    pipeline = _build_pipeline(args)
    if args.web_search:
        object.__setattr__(pipeline._config, "web_search_enabled", True)
    if args.fetch_pages:
        object.__setattr__(pipeline._config, "web_fetch_enabled", True)
    result = pipeline.run_discovered_batch(
        source=args.source,
        days_back=args.days_back,
        limit=args.limit,
        seed_file=args.seed_file,
    )
    ok = sum(1 for r in result if "error" not in r)
    failed = sum(1 for r in result if "error" in r)
    print(f"Discovered batch complete: {ok} ok, {failed} failed")
    for r in result:
        status = "OK" if "error" not in r else f"FAIL: {r['error']}"
        title = r.get("title", r.get("registry_number", "?"))
        print(f"  [{status}] {title}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Tender Research Pipeline CLI")
    parser.add_argument("--data-dir", default=None, help="Data directory override")
    sub = parser.add_subparsers(dest="command", required=True)

    p_stats = sub.add_parser("stats", help="Show pipeline statistics")

    p_check = sub.add_parser("check-eis-config", help="Check EIS SOAP configuration and available methods")

    _common = argparse.ArgumentParser(add_help=False)
    _common.add_argument("--eis-mode", default=None, choices=["demo", "real"], help="EIS loader mode")

    p_ingest = sub.add_parser("ingest-eis", parents=[_common], help="Ingest tenders from EIS")
    p_ingest.add_argument("--date-from", default=None, help="ISO date (e.g. 2026-07-01)")
    p_ingest.add_argument("--date-to", default=None, help="ISO date")
    p_ingest.add_argument("--limit", type=int, default=None, help="Max tenders")
    p_ingest.add_argument("--law-type", default=None, help="44fz / 223fz")
    p_ingest.add_argument("--query", default=None, help="Search query")

    p_batch = sub.add_parser("research-batch", parents=[_common], help="Full cycle for a batch of tenders")
    p_batch.add_argument("--date-from", default=None)
    p_batch.add_argument("--date-to", default=None)
    p_batch.add_argument("--limit", type=int, default=None)
    p_batch.add_argument("--law-type", default=None)
    p_batch.add_argument("--query", default=None)
    p_batch.add_argument("--web-search", action="store_true", help="Enable web search")

    p_reg = sub.add_parser("ingest-eis-registry-list", parents=[_common], help="Ingest tenders by registry number list")
    p_reg.add_argument("--file", default="data/eis_seed/registry_numbers.txt", help="Path to seed file")
    p_reg.add_argument("--limit", type=int, default=None, help="Max tenders to process")

    p_one = sub.add_parser("research-one", parents=[_common], help="Full cycle for one tender")
    p_one.add_argument("external_id", help="EIS external ID")

    p_q = sub.add_parser("build-queries", help="Build search queries for a tender")
    p_q.add_argument("tender_id", help="Tender UUID (id)")

    p_ws = sub.add_parser("web-search", help="Run web search for a tender")
    p_ws.add_argument("tender_id", help="Tender UUID")

    p_fp = sub.add_parser("fetch-pages", help="Fetch pages from search results")
    p_fp.add_argument("tender_id", help="Tender UUID")
    p_fp.add_argument("--limit", type=int, default=10, help="Max pages to fetch")

    p_disc = sub.add_parser("discover-registry-numbers", parents=[_common], help="Discover registry numbers from EIS sources")
    p_disc.add_argument("--source", default="auto", choices=["auto", "backend_search", "eis_public_html", "seed_file"],
                        help="Discovery source (default: auto)")
    p_disc.add_argument("--days-back", type=int, default=None, help="Days to look back")
    p_disc.add_argument("--limit", type=int, default=10, help="Max numbers to discover")
    p_disc.add_argument("--seed-file", default=None, help="Path to seed file (for seed_file source)")
    p_disc.add_argument("--output", default=None, help="Save non-demo numbers to file (e.g. data/eis_seed/registry_numbers_auto.txt)")

    p_disc_batch = sub.add_parser("research-discovered", parents=[_common],
                                   help="Discover and research tenders in one step")
    p_disc_batch.add_argument("--source", default="auto", choices=["auto", "backend_search", "eis_public_html", "seed_file"])
    p_disc_batch.add_argument("--days-back", type=int, default=None)
    p_disc_batch.add_argument("--limit", type=int, default=10)
    p_disc_batch.add_argument("--seed-file", default=None, help="Path to seed file (for seed_file source)")
    p_disc_batch.add_argument("--web-search", action="store_true", help="Enable web search")
    p_disc_batch.add_argument("--fetch-pages", action="store_true", help="Fetch web pages")

    args = parser.parse_args()

    if args.command == "stats":
        cmd_stats(args)
    elif args.command == "check-eis-config":
        cmd_check_eis_config(args)
    elif args.command == "ingest-eis":
        cmd_ingest_eis(args)
    elif args.command == "ingest-eis-registry-list":
        cmd_ingest_eis_registry_list(args)
    elif args.command == "research-batch":
        cmd_research_batch(args)
    elif args.command == "research-one":
        cmd_research_one(args)
    elif args.command == "build-queries":
        cmd_build_queries(args)
    elif args.command == "web-search":
        cmd_web_search(args)
    elif args.command == "fetch-pages":
        cmd_fetch_pages(args)
    elif args.command == "discover-registry-numbers":
        cmd_discover_registry_numbers(args)
    elif args.command == "research-discovered":
        cmd_research_discovered(args)


if __name__ == "__main__":
    main()
