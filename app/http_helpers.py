from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request

from .auth_storage import get_user_by_id


_RATE_LIMIT_BUCKETS: dict[str, list[float]] = defaultdict(list)


def data_response(payload: dict) -> dict:
    return {"data": payload}


def deferred_feature_response(feature_key: str, message: str, *, success: bool = False, **payload) -> dict:
    response_payload = {
        "Success": success,
        "FeatureStatus": "deferred",
        "DeferredFeature": feature_key,
        "Msg": message,
    }
    response_payload.update(payload)
    return data_response(response_payload)


def deferred_feature_headers(feature_key: str) -> dict[str, str]:
    return {
        "X-Feature-Status": "deferred",
        "X-Deferred-Feature": feature_key,
    }


def require_user(request: Request) -> dict:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = get_user_by_id(request.app.state.db, user_id)
    if not user:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def allow_rate_limited_request(request: Request) -> bool:
    settings = request.app.state.settings
    client_host = request.client.host if request.client else "unknown"
    bucket_key = f"{request.url.path}:{client_host}"
    now = time.monotonic()
    window_start = now - settings.auth_rate_limit_window_seconds
    recent_attempts = [stamp for stamp in _RATE_LIMIT_BUCKETS[bucket_key] if stamp >= window_start]
    if len(recent_attempts) >= settings.auth_rate_limit_max_attempts:
        _RATE_LIMIT_BUCKETS[bucket_key] = recent_attempts
        return False
    recent_attempts.append(now)
    _RATE_LIMIT_BUCKETS[bucket_key] = recent_attempts
    return True


def reset_rate_limit_buckets() -> None:
    _RATE_LIMIT_BUCKETS.clear()


def set_default_security_headers(headers, enabled: bool) -> None:
    if not enabled:
        return
    headers["X-Content-Type-Options"] = "nosniff"
    headers["Referrer-Policy"] = "same-origin"
    headers["Cross-Origin-Opener-Policy"] = "same-origin"
    headers["Cross-Origin-Resource-Policy"] = "same-site"
