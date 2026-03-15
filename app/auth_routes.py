from __future__ import annotations

import secrets
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from .auth_storage import authenticate_password_user, create_password_user, update_user_password, upsert_google_user
from .http_helpers import data_response, require_user
from .schemas import AuthCredentialsPayload, ForgotPasswordPayload, PasswordUpdatePayload, ProviderLoginPayload, ResetPasswordPayload


router = APIRouter()


PASSWORD_MIN_LENGTH = 7
PASSWORD_MAX_LENGTH = 255


@router.get("/rest/v1/auth/oauth2/link")
async def get_google_link(request: Request, Provider: str) -> dict:
    if Provider.lower() != "google":
        return data_response({"Success": False, "Msg": "Unsupported provider."})
    settings = request.app.state.settings
    if not settings.google_client_id or not settings.google_client_secret:
        return data_response({"Success": False, "Msg": "Google OAuth is not configured."})
    return data_response({"Success": True, "Link": f"{settings.backend_base_url}/auth/google/start"})


@router.get("/auth/google/start")
async def start_google_login(request: Request) -> RedirectResponse:
    settings = request.app.state.settings
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured.")
    state = secrets.token_urlsafe(24)
    request.session["oauth_state"] = state
    query = urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "select_account",
            "access_type": "offline",
        }
    )
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{query}", status_code=302)


@router.get("/auth/google/callback")
async def finish_google_login(request: Request, code: Optional[str] = None, state: Optional[str] = None) -> HTMLResponse:
    settings = request.app.state.settings
    expected_state = request.session.get("oauth_state")
    if not code or not state or expected_state != state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state.")
    async with httpx.AsyncClient(timeout=15) as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        token_response.raise_for_status()
        tokens = token_response.json()
        profile_response = await client.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        profile_response.raise_for_status()
        profile = profile_response.json()
    user = upsert_google_user(
        request.app.state.db,
        google_sub=profile["sub"],
        email=profile["email"],
        name=profile.get("name"),
        picture_url=profile.get("picture"),
    )
    request.session["user_id"] = user["id"]
    request.session.pop("oauth_state", None)
    html = """
    <html><body style="font-family:sans-serif;padding:32px">
    <h2>NotebookLM Capture Organize</h2>
    <p>Google sign-in succeeded. You can close this window.</p>
    <script>window.close();</script>
    </body></html>
    """
    return HTMLResponse(html)


@router.post("/rest/v1/users")
async def register(request: Request, payload: AuthCredentialsPayload) -> dict:
    if not _validate_password_length(payload.Password):
        return data_response({"Success": False, "MsgCode": _password_length_error(payload.Password)})
    user, error = create_password_user(request.app.state.db, payload.normalized_email(), payload.Password)
    if not user:
        return data_response({"Success": False, "Msg": error or "Unable to create your account."})
    request.session["user_id"] = user["id"]
    return data_response({"Success": True, "Email": user["email"]})


@router.post("/rest/v1/auth/login")
async def login(request: Request, payload: AuthCredentialsPayload) -> dict:
    user = authenticate_password_user(request.app.state.db, payload.normalized_email(), payload.Password)
    if not user:
        return data_response({"Success": False, "Msg": "Invalid email or password."})
    request.session["user_id"] = user["id"]
    return data_response({"Success": True, "Email": user["email"]})


@router.get("/rest/v1/auth/is-logged-in")
async def is_logged_in(request: Request) -> dict:
    user_id = request.session.get("user_id")
    return data_response({"IsLoggedIn": bool(user_id)})


@router.get("/rest/v1/auth/logout")
async def logout(request: Request) -> dict:
    request.session.clear()
    return data_response({"Success": True})


@router.post("/rest/v1/auth/oauth2/login")
async def provider_login(_: Request, payload: ProviderLoginPayload) -> dict:
    provider = (payload.Provider or "").lower()
    if provider and provider != "google":
        return data_response({"Success": False, "Msg": "Unsupported provider."})
    return data_response({"Success": False, "Msg": "Use the oauth2/link flow for Google sign-in."})


@router.get("/rest/v1/users/info")
async def user_info(request: Request) -> dict:
    user = require_user(request)
    return data_response(
        {
            "Success": True,
            "Email": user["email"],
            "Name": user["name"],
            "PictureURL": user["picture_url"],
            "AuthProvider": user.get("auth_provider") or "google",
            "HasPassword": bool(user.get("password_hash")),
        }
    )


@router.post("/rest/v1/users/update-password")
async def update_password(request: Request, payload: PasswordUpdatePayload) -> dict:
    user = require_user(request)
    if not payload.OldPassword and user.get("password_hash"):
        return data_response({"Success": False, "MsgCode": 1046})
    if not payload.NewPassword:
        return data_response({"Success": False, "MsgCode": 1047})
    if not _validate_password_length(payload.NewPassword):
        return data_response({"Success": False, "MsgCode": _password_length_error(payload.NewPassword)})
    success = update_user_password(request.app.state.db, user["id"], payload.OldPassword, payload.NewPassword)
    return data_response({"Success": success, "MsgCode": None if success else 1050})


@router.post("/rest/v1/users/forgot-password")
async def forgot_password(_: Request, payload: ForgotPasswordPayload) -> dict:
    username = payload.Username.strip()
    if not username:
        return data_response({"Success": False, "MsgCode": 1055})
    if "@" not in username:
        return data_response({"Success": False, "MsgCode": 1056})
    return data_response({"Success": True, "MsgCode": 1057})


@router.post("/rest/v1/users/reset-password")
async def reset_password(_: Request, payload: ResetPasswordPayload) -> dict:
    if not payload.ResetCode.strip():
        return data_response({"Success": False, "MsgCode": 1051})
    if not _validate_password_length(payload.NewPassword):
        return data_response({"Success": False, "MsgCode": _password_length_error(payload.NewPassword)})
    return data_response({"Success": False, "MsgCode": 1054})


def _validate_password_length(password: str) -> bool:
    return PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH


def _password_length_error(password: str) -> int:
    return 1048 if len(password) < PASSWORD_MIN_LENGTH else 1049
