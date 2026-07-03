import base64
import secrets

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.shared.config.settings import Settings


TENDER_PILOT_ROUTE_PREFIXES = (
    "/demo/tender-agent",
    "/pilot/tender-agent",
    "/api/demo/tender-agent",
)


class TenderPilotBasicAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, username: str, password: str) -> None:
        super().__init__(app)
        self.username = username
        self.password = password

    async def dispatch(self, request: Request, call_next) -> Response:
        if not _is_protected_tender_pilot_path(request.url.path):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if auth_header is None:
            return _build_unauthorized_response()

        scheme, _, encoded_credentials = auth_header.partition(" ")
        if scheme.lower() != "basic" or not encoded_credentials:
            return _build_unauthorized_response()

        try:
            decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return _build_unauthorized_response()

        username, _, password = decoded_credentials.partition(":")
        if not (
            secrets.compare_digest(username, self.username)
            and secrets.compare_digest(password, self.password)
        ):
            return _build_unauthorized_response()

        return await call_next(request)


def install_runtime_middlewares(app: FastAPI, settings: Settings) -> None:
    allowed_hosts = settings.allowed_hosts_list()
    if allowed_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

    cors_allow_origins = settings.cors_allow_origins_list()
    if cors_allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_allow_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    if settings.tender_pilot_basic_auth_enabled:
        if not settings.tender_pilot_basic_auth_username or not settings.tender_pilot_basic_auth_password:
            raise RuntimeError(
                "Tender pilot basic auth is enabled, but username/password are not fully configured."
            )
        app.add_middleware(
            TenderPilotBasicAuthMiddleware,
            username=settings.tender_pilot_basic_auth_username,
            password=settings.tender_pilot_basic_auth_password,
        )


def _is_protected_tender_pilot_path(path: str) -> bool:
    return any(path == prefix or path.startswith(f"{prefix}/") for prefix in TENDER_PILOT_ROUTE_PREFIXES)


def _build_unauthorized_response() -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"detail": "Authentication required for tender pilot routes."},
        headers={"WWW-Authenticate": 'Basic realm="Tender Pilot"'},
    )
