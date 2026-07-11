import base64

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.shared.api.middleware import install_runtime_middlewares
from src.shared.config.settings import Settings


def _auth(username: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def test_r0_pilot_boundary_keeps_health_public_and_protects_api_and_ready() -> None:
    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/example")
    def api():
        return {"ok": True}

    @app.get("/health/ready")
    def ready():
        return {"status": "ok"}

    install_runtime_middlewares(app, Settings(pilot_auth_enabled=True, pilot_auth_username="pilot", pilot_auth_password="long-test-password", allowed_hosts="", cors_allow_origins=""))
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/api/example").status_code == 401
    assert client.get("/health/ready").status_code == 401
    response = client.get("/api/example", headers=_auth("pilot", "long-test-password"))
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_r0_rejects_placeholder_pilot_password() -> None:
    app = FastAPI()
    try:
        install_runtime_middlewares(app, Settings(pilot_auth_enabled=True, pilot_auth_username="pilot", pilot_auth_password="CHANGE_ME"))
    except RuntimeError:
        pass
    else:
        raise AssertionError("placeholder password must be rejected")
