from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import time
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from .auth_routes import router as auth_router
from .config import Settings, load_settings
from .database import initialize_database, open_connection
from .http_helpers import allow_rate_limited_request, data_response, set_default_security_headers
from .optional_feature_routes import router as optional_feature_router
from .organize_routes import router as organize_router
from .public_site_routes import router as public_site_router


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("notebooklm-capture-organize.backend")

AUTH_RATE_LIMIT_PATHS = {
    "/rest/v1/users",
    "/rest/v1/auth/login",
    "/rest/v1/users/forgot-password",
    "/rest/v1/users/reset-password",
}


def create_app(settings_override: Settings | None = None) -> FastAPI:
    settings = settings_override or load_settings()
    initialize_database(settings.database_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            yield
        finally:
            db = getattr(app.state, "db", None)
            if db is not None:
                db.close()

    app = FastAPI(title="NotebookLM Capture Organize Backend", version="0.3.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=settings.cors_allow_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        same_site="none" if settings.cookie_secure else "lax",
        https_only=settings.cookie_secure,
        session_cookie=settings.session_cookie_name,
        max_age=settings.session_max_age_seconds,
    )
    app.state.settings = settings
    app.state.db = open_connection(settings.database_path)
    app.include_router(public_site_router)
    app.include_router(auth_router)
    app.include_router(organize_router)
    app.include_router(optional_feature_router)

    @app.middleware("http")
    async def request_observability_middleware(request, call_next):
        request_id = uuid.uuid4().hex
        start = time.perf_counter()
        if request.url.path in AUTH_RATE_LIMIT_PATHS and not allow_rate_limited_request(request):
            response = JSONResponse(
                status_code=429,
                content=data_response({"Success": False, "Msg": "Too many authentication attempts. Please wait and try again."}),
            )
        else:
            response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        if request.url.path.startswith("/rest/v1"):
            response.headers["Cache-Control"] = "no-store"
        set_default_security_headers(response.headers, settings.security_headers_enabled)
        if settings.request_log_enabled:
            logger.info("%s %s %s %.2fms", request.method, request.url.path, response.status_code, duration_ms)
        return response

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/rest/v1/extension/info")
    async def extension_info() -> dict:
        return data_response(
            {
                "Success": True,
                "ProductName": "NotebookLM Capture Organize",
                "BackendBaseURL": settings.backend_base_url,
                "Features": ["google-login", "folders", "notebooks", "captures"],
                "Mode": "notebooklm-companion",
                "OwnedFeatures": ["auth", "organize", "capture-metadata", "notebook-folder-mapping"],
                "DeferredFeatures": [
                    "billing",
                    "onedrive-connector",
                    "youtube-import-helper",
                    "source-document-mirror",
                    "sec-financial-report-mirror",
                ],
                "OptionalHostAccessMode": "pinned-hosts",
                "AllowedBackendOrigins": [
                    "http://127.0.0.1:8787",
                    "http://localhost:8787",
                    "https://140.245.110.91.sslip.io",
                ],
                "CompanionTarget": "https://notebooklm.google.com",
                "DeploymentProvider": "oracle-cloud-compute",
                "SupportURL": settings.support_url,
                "PrivacyPolicyURL": settings.privacy_policy_url,
                "ReviewerNotesURL": settings.reviewer_notes_url,
            }
        )

    return app


app = create_app()
