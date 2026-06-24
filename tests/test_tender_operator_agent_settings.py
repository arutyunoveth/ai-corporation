from src.modules.tender_operator_agent_demo.settings import (
    ZakupkiSoapSettings,
    clear_zakupki_soap_settings_cache,
    get_zakupki_soap_settings,
    is_zakupki_soap_configured,
)


def test_zakupki_soap_disabled_without_token(monkeypatch):
    monkeypatch.delenv("ZAKUPKI_GOV_RU_SOAP_ENABLED", raising=False)
    monkeypatch.delenv("ZAKUPKI_GOV_RU_SOAP_TOKEN", raising=False)
    monkeypatch.delenv("ZAKUPKI_GOV_RU_SOAP_TOKEN_OWNER", raising=False)
    clear_zakupki_soap_settings_cache()

    settings = get_zakupki_soap_settings()

    assert settings.enabled is False
    assert settings.configured is False
    assert settings.token_owner == "individual"
    assert settings.active_docs_endpoint == "https://int.zakupki.gov.ru/eis-integration/services/getDocsIP"
    assert settings.individual_namespace == "http://zakupki.gov.ru/fz44/get-docs-ip/ws"
    assert settings.disable_proxy_for_eis is True
    assert settings.require_direct_ru_route is True
    assert settings.use_soap_action is True
    assert settings.soap_action_uri == "http://zakupki.gov.ru/fz44/queue/ws/get-docs-ip"
    assert is_zakupki_soap_configured(settings) is False
    assert "не настроен" in settings.safe_status()["reason"]


def test_placeholder_token_is_not_configured(monkeypatch):
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_ENABLED", "1")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_TOKEN", "replace_me_do_not_commit_real_token")
    clear_zakupki_soap_settings_cache()

    settings = get_zakupki_soap_settings()

    assert settings.enabled is True
    assert settings.configured is False
    assert is_zakupki_soap_configured(settings) is False


def test_real_looking_env_token_is_configured(monkeypatch):
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_ENABLED", "true")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_TOKEN", "test-token-value-not-real")
    clear_zakupki_soap_settings_cache()

    settings = get_zakupki_soap_settings()

    assert settings.configured is True
    assert is_zakupki_soap_configured(settings) is True


def test_token_is_not_in_repr_or_safe_status():
    settings = ZakupkiSoapSettings(enabled=True, token="secret-token-value")

    assert "secret-token-value" not in repr(settings)
    assert "secret-token-value" not in str(settings.safe_status())


def test_custom_actions_and_debug_flags_are_read_from_env(monkeypatch):
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_ENABLED", "1")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_TOKEN", "test-token-value-not-real")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_TOKEN_OWNER", "individual")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_SEARCH_ACTION", "urn:Search")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_DETAILS_ACTION", "urn:Details")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_ATTACHMENTS_ACTION", "urn:Attachments")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_TRUST_ENV_PROXY", "1")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_DEBUG", "1")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_DISABLE_PROXY_FOR_EIS", "0")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_USE_SOAP_ACTION", "1")
    clear_zakupki_soap_settings_cache()

    settings = get_zakupki_soap_settings()

    assert settings.search_action == "urn:Search"
    assert settings.details_action == "urn:Details"
    assert settings.attachments_action == "urn:Attachments"
    assert settings.trust_env_proxy is True
    assert settings.debug is True
    assert settings.disable_proxy_for_eis is False
    assert settings.use_soap_action is True


def test_individual_owner_settings_are_read_from_env(monkeypatch):
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_ENABLED", "1")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_TOKEN", "test-token-value-not-real")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_TOKEN_OWNER", "individual")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_INDIVIDUAL_BASE_URL", "https://example.test/getDocsIP")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_INDIVIDUAL_NAMESPACE", "http://example.test/ws")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_TOKEN_HEADER_NAME", "individualPerson_token")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_MODE", "PROD")
    clear_zakupki_soap_settings_cache()

    settings = get_zakupki_soap_settings()

    assert settings.token_owner == "individual"
    assert settings.active_docs_endpoint == "https://example.test/getDocsIP"
    assert settings.individual_namespace == "http://example.test/ws"
    assert settings.token_header_name == "individualPerson_token"
    assert settings.mode == "PROD"


def test_allowed_hosts_and_user_agent_are_read(monkeypatch):
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_ENABLED", "1")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_TOKEN", "test-token-value-not-real")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_ALLOWED_HOSTS", "zakupki.gov.ru,.zakupki.gov.ru,int.zakupki.gov.ru")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_USER_AGENT", "ArvectumTenderAgent/0.1 read-only")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_CONTENT_TYPE", "text/xml; charset=utf-8")
    clear_zakupki_soap_settings_cache()

    settings = get_zakupki_soap_settings()

    assert "zakupki.gov.ru" in settings.allowed_hosts
    assert ".zakupki.gov.ru" in settings.allowed_hosts
    assert settings.user_agent == "ArvectumTenderAgent/0.1 read-only"
    assert settings.content_type == "text/xml; charset=utf-8"
