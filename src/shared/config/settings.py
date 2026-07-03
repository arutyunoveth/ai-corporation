from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Corporation Sprint 1 API"
    debug: bool = False
    database_url: str = "sqlite:///./ai_corporation.db"
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
    cloudru_api_key: str | None = None
    cloudru_base_url: str = "https://foundation-models.api.cloud.ru/v1"
    gigachat_auth_key: str | None = None
    gigachat_scope: str = "GIGACHAT_API_PERS"
    gigachat_oauth_url: str = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    gigachat_base_url: str = "https://gigachat.devices.sberbank.ru/api/v1"

    model_config = SettingsConfigDict(
        env_prefix="AI_CORP_",
        env_file=".env",
        extra="ignore",
    )

    def allowed_hosts_list(self) -> list[str]:
        return _split_csv(self.allowed_hosts)

    def cors_allow_origins_list(self) -> list[str]:
        return _split_csv(self.cors_allow_origins)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def _split_csv(raw_value: str) -> list[str]:
    return [item.strip() for item in raw_value.split(",") if item.strip()]
