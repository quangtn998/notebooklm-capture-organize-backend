from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _read_env_file() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_read_env_file()


@dataclass(frozen=True)
class Settings:
    backend_base_url: str
    database_path: Path
    session_secret: str
    google_client_id: str
    google_client_secret: str
    public_support_email: str
    cookie_secure: bool
    cors_allow_origin_regex: str
    session_cookie_name: str
    session_max_age_seconds: int
    auth_rate_limit_window_seconds: int
    auth_rate_limit_max_attempts: int
    request_log_enabled: bool
    security_headers_enabled: bool

    @property
    def google_redirect_uri(self) -> str:
        return f"{self.backend_base_url}/auth/google/callback"

    @property
    def support_url(self) -> str:
        return f"{self.backend_base_url}/support"

    @property
    def privacy_policy_url(self) -> str:
        return f"{self.backend_base_url}/privacy-policy"

    @property
    def reviewer_notes_url(self) -> str:
        return f"{self.backend_base_url}/reviewer-notes"


def load_settings() -> Settings:
    default_db = Path(__file__).resolve().parents[1] / "data" / "notebooklm-capture-organize.sqlite3"
    return Settings(
        backend_base_url=os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8787").rstrip("/"),
        database_path=Path(os.getenv("BACKEND_DATABASE_PATH", str(default_db))),
        session_secret=os.getenv("BACKEND_SESSION_SECRET", "change-this-session-secret"),
        google_client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
        google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
        public_support_email=os.getenv("PUBLIC_SUPPORT_EMAIL", "").strip(),
        cookie_secure=os.getenv("BACKEND_COOKIE_SECURE", "false").lower() == "true",
        cors_allow_origin_regex=os.getenv(
            "BACKEND_CORS_ALLOW_ORIGIN_REGEX",
            r"chrome-extension://.*|http://127\.0\.0\.1(:\d+)?|http://localhost(:\d+)?",
        ),
        session_cookie_name=os.getenv("BACKEND_SESSION_COOKIE_NAME", "nlmco_session"),
        session_max_age_seconds=int(os.getenv("BACKEND_SESSION_MAX_AGE_SECONDS", "1209600")),
        auth_rate_limit_window_seconds=int(os.getenv("BACKEND_AUTH_RATE_LIMIT_WINDOW_SECONDS", "300")),
        auth_rate_limit_max_attempts=int(os.getenv("BACKEND_AUTH_RATE_LIMIT_MAX_ATTEMPTS", "10")),
        request_log_enabled=os.getenv("BACKEND_REQUEST_LOG_ENABLED", "true").lower() == "true",
        security_headers_enabled=os.getenv("BACKEND_SECURITY_HEADERS_ENABLED", "true").lower() == "true",
    )
