from __future__ import annotations

from dataclasses import dataclass, field

from src.shared.config.settings import get_settings


@dataclass
class TenderResearchConfig:
    enabled: bool = True
    batch_limit: int = 10
    eis_mode: str = "demo"
    eis_discovery_mode: str = "registry_numbers"
    eis_seed_file: str = "data/eis_seed/registry_numbers.txt"

    registry_discovery_source: str = "auto"
    registry_discovery_days_back: int = 3
    registry_discovery_limit: int = 10
    public_search_enabled: bool = True
    public_search_use_playwright: bool = False
    public_search_delay_seconds: float = 3.0
    public_search_timeout_seconds: int = 30
    public_search_bypass_proxy: bool = False
    public_search_page_size: int = 30
    public_search_no_proxy_domains: str = "zakupki.gov.ru,.zakupki.gov.ru,int.zakupki.gov.ru,int44.zakupki.gov.ru"
    allow_demo_discovery: bool = True

    web_search_enabled: bool = False
    web_search_provider: str = "duckduckgo_html"
    web_search_max_queries_per_tender: int = 8
    web_search_max_results_per_query: int = 10
    web_search_delay_seconds: float = 3.0
    web_search_timeout_seconds: int = 20

    web_fetch_enabled: bool = True
    web_fetch_max_pages_per_tender: int = 20
    web_fetch_delay_seconds: float = 2.0
    web_fetch_timeout_seconds: int = 30
    web_fetch_max_file_size_mb: int = 25

    use_playwright: bool = False
    web_save_screenshots: bool = False
    web_deny_domains: str = ""
    web_allow_domains: str = ""

    document_download_max_size_mb: int = 100
    document_extract_max_chars: int = 2_000_000

    data_dir: str = "./data"

    deny_domain_list: tuple[str, ...] = field(default_factory=lambda: (
        "localhost", "127.0.0.1", "0.0.0.0", "::1",
        "10.", "172.16.", "172.17.", "172.18.", "172.19.",
        "172.20.", "172.21.", "172.22.", "172.23.",
        "172.24.", "172.25.", "172.26.", "172.27.",
        "172.28.", "172.29.", "172.30.", "172.31.",
        "192.168.",
    ))


def load_config() -> TenderResearchConfig:
    s = get_settings()
    return TenderResearchConfig(
        enabled=s.tender_research_enabled,
        batch_limit=s.tender_research_batch_limit,
        eis_mode=s.tender_research_eis_mode,
        eis_discovery_mode=s.tender_research_eis_discovery_mode,
        eis_seed_file=s.tender_research_eis_seed_file,
        registry_discovery_source=s.registry_discovery_source,
        registry_discovery_days_back=s.registry_discovery_days_back,
        registry_discovery_limit=s.registry_discovery_limit,
        public_search_enabled=s.public_search_enabled,
        public_search_use_playwright=s.public_search_use_playwright,
        public_search_delay_seconds=s.public_search_delay_seconds,
        public_search_timeout_seconds=s.public_search_timeout_seconds,
        public_search_bypass_proxy=s.public_search_bypass_proxy,
        public_search_page_size=s.public_search_page_size,
        public_search_no_proxy_domains=s.public_search_no_proxy_domains,
        allow_demo_discovery=s.allow_demo_discovery,
        web_search_enabled=s.web_search_enabled,
        web_search_provider=s.web_search_provider,
        web_search_max_queries_per_tender=s.web_search_max_queries_per_tender,
        web_search_max_results_per_query=s.web_search_max_results_per_query,
        web_search_delay_seconds=s.web_search_delay_seconds,
        web_search_timeout_seconds=s.web_search_timeout_seconds,
        web_fetch_enabled=s.web_fetch_enabled,
        web_fetch_max_pages_per_tender=s.web_fetch_max_pages_per_tender,
        web_fetch_delay_seconds=s.web_fetch_delay_seconds,
        web_fetch_timeout_seconds=s.web_fetch_timeout_seconds,
        web_fetch_max_file_size_mb=s.web_fetch_max_file_size_mb,
        use_playwright=s.web_use_playwright,
        web_save_screenshots=s.web_save_screenshots,
        web_deny_domains=s.web_deny_domains,
        web_allow_domains=s.web_allow_domains,
        document_download_max_size_mb=s.document_download_max_size_mb,
        document_extract_max_chars=s.document_extract_max_chars,
        data_dir=s.arvectum_data_dir,
    )
