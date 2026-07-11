import base64
import hmac

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.shared.config.settings import Settings

DEFAULT_PROTECTED_PREFIXES = ("/demo/tender-agent", "/pilot/tender-agent", "/api/demo/tender-agent")
DEFAULT_PUBLIC_PATHS = ("/health",)

class TenderPilotBasicAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, username: str, password: str, protected: tuple[str, ...] = DEFAULT_PROTECTED_PREFIXES, public: tuple[str, ...] = DEFAULT_PUBLIC_PATHS) -> None:
        super().__init__(app)
        self.username = username
        self.password = password
        self.protected = protected
        self.public = public

    async def dispatch(self, request: Request, call_next) -> Response:
        if not _is_protected_path(request.url.path, self.protected, self.public):
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
            hmac.compare_digest(username, self.username)
            and hmac.compare_digest(password, self.password)
        ):
            return _build_unauthorized_response()
        response = await call_next(request)
        response.headers.update({"Cache-Control": "no-store", "Pragma": "no-cache", "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer"})
        return response


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

    if settings.pilot_auth_is_enabled():
        username, password = settings.pilot_auth_credentials()
        if not username or not settings.pilot_auth_password_safe():
            raise RuntimeError(
                "Pilot auth is enabled but username/password are incomplete or placeholder values."
            )
        app.add_middleware(
            TenderPilotBasicAuthMiddleware,
            username=username,
            password=password,
            protected=tuple(settings.pilot_auth_protected_prefixes.split(",")),
            public=tuple(settings.pilot_auth_public_paths.split(",")),
        )


def _is_protected_path(path: str, protected: tuple[str, ...], public: tuple[str, ...]) -> bool:
    if path in public:
        return False
    return any(path == prefix or path.startswith(f"{prefix}/") for prefix in protected if prefix)


def _build_unauthorized_response() -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"detail": "Authentication required for tender pilot routes."},
        headers={"WWW-Authenticate": 'Basic realm="Tender Pilot"'},
    )
