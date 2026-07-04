from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Corporation Sprint 1 API"
    debug: bool = False
    database_url: str = "sqlite:///./ai_corporation.db"
    site_public_root: str | None = None
    allowed_hosts: str = ""
    cors_allow_origins: str = ""
    tender_pilot_basic_auth_enabled: bool = False
    tender_pilot_basic_auth_username: str | None = None
    tender_pilot_basic_auth_password: str | None = None
    llm_provider: str = "stub"
    llm_model: str | None = None
    llm_timeout_seconds: int = 30
    llm_max_retries: int = 1
    llm_allow_raw_partner_data: bool = False
    llm_store_raw_response: bool = False
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    yandex_api_key: str | None = None
    yandex_iam_token: str | None = None
    yandex_base_url: str = "https://ai.api.cloud.yandex.net/v1"
    yandex_search_api_key: str | None = None
    yandex_search_folder_id: str | None = None
    cloudru_api_key: str | None = None
    cloudru_base_url: str = "https://foundation-models.api.cloud.ru/v1"
    gigachat_auth_key: str | None = None
    gigachat_scope: str = "GIGACHAT_API_PERS"
    gigachat_oauth_url: str = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    gigachat_base_url: str = "https://gigachat.devices.sberbank.ru/api/v1"

    arvectum_data_dir: str = "./data"
    tender_research_enabled: bool = True
    tender_research_batch_limit: int = 10
    tender_research_eis_mode: str = "demo"
    tender_research_eis_discovery_mode: str = "registry_numbers"
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
    web_use_playwright: bool = False
    web_save_screenshots: bool = False
    web_deny_domains: str = ""
    web_allow_domains: str = ""
    document_download_max_size_mb: int = 100
    document_extract_max_chars: int = 2_000_000

    model_config = SettingsConfigDict(
        env_prefix="AI_CORP_",
        env_file=[".env", ".env.local"],
        extra="ignore",
    )

    def allowed_hosts_list(self) -> list[str]:
        return _split_csv(self.allowed_hosts)

    def cors_allow_origins_list(self) -> list[str]:
        return _split_csv(self.cors_allow_origins)

    def site_public_root_path(self) -> Path | None:
        if not self.site_public_root:
            return None
        return Path(self.site_public_root).expanduser().resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def _split_csv(raw_value: str) -> list[str]:
    return [item.strip() for item in raw_value.split(",") if item.strip()]
