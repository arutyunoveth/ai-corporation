import base64

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.shared.api.middleware import TenderPilotBasicAuthMiddleware, install_runtime_middlewares
from src.shared.config.settings import Settings


def _build_basic_auth_header(username: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def test_tender_pilot_basic_auth_protects_only_pilot_routes() -> None:
    app = FastAPI()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/demo/tender-agent")
    def pilot() -> dict[str, str]:
        return {"status": "pilot"}

    app.add_middleware(TenderPilotBasicAuthMiddleware, username="pilot", password="secret")
    client = TestClient(app)

    health_response = client.get("/health")
    assert health_response.status_code == 200

    pilot_response = client.get("/demo/tender-agent")
    assert pilot_response.status_code == 401
    assert pilot_response.headers["www-authenticate"] == 'Basic realm="Tender Pilot"'

    authorized_response = client.get(
        "/demo/tender-agent",
        headers=_build_basic_auth_header("pilot", "secret"),
    )
    assert authorized_response.status_code == 200
    assert authorized_response.json() == {"status": "pilot"}


def test_install_runtime_middlewares_rejects_incomplete_basic_auth_config() -> None:
    app = FastAPI()
    settings = Settings(
        tender_pilot_basic_auth_enabled=True,
        tender_pilot_basic_auth_username="pilot",
        tender_pilot_basic_auth_password=None,
    )

    try:
        install_runtime_middlewares(app, settings)
    except RuntimeError as exc:
        assert "username/password" in str(exc)
    else:
        raise AssertionError("Expected runtime middleware installation to fail without password")


def test_install_runtime_middlewares_accepts_csv_settings() -> None:
    settings = Settings(
        allowed_hosts="arvectum.com, www.arvectum.com",
        cors_allow_origins="https://arvectum.com, https://www.arvectum.com",
    )

    assert settings.allowed_hosts_list() == ["arvectum.com", "www.arvectum.com"]
    assert settings.cors_allow_origins_list() == [
        "https://arvectum.com",
        "https://www.arvectum.com",
    ]
