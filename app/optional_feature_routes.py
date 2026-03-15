from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from .http_helpers import deferred_feature_headers, deferred_feature_response


router = APIRouter(prefix="/rest/v1")


@router.get("/payments/buy")
async def payments_buy() -> dict:
    return deferred_feature_response("billing", "Billing is not configured for this build.")


@router.get("/payments/users/plan-features")
async def payments_plan_features() -> dict:
    return deferred_feature_response(
        "billing",
        "Billing is not configured for this build.",
        success=True,
        Features=[],
    )


@router.get("/payments/users/plan")
async def payments_user_plan() -> dict:
    return deferred_feature_response(
        "billing",
        "Billing is not configured for this build.",
        success=True,
        Plan={"Name": "free", "Status": "active", "Source": "local-default"},
    )


@router.get("/payments/plans")
async def payments_plans() -> dict:
    return deferred_feature_response(
        "billing",
        "Billing is not configured for this build.",
        success=True,
        Plans=[],
    )


@router.patch("/payments/subscriptions")
async def payments_subscriptions() -> dict:
    return deferred_feature_response("billing", "Billing is not configured for this build.")


@router.get("/oauth2/onedrive/auth-url")
async def onedrive_auth_url() -> dict:
    return deferred_feature_response("onedrive-connector", "OneDrive is not configured for this build.")


@router.post("/oauth2/onedrive/verify-and-get-url")
async def onedrive_verify() -> dict:
    return deferred_feature_response("onedrive-connector", "OneDrive is not configured for this build.")


@router.get("/external/youtube/videos")
async def youtube_videos() -> dict:
    return deferred_feature_response(
        "youtube-import-helper",
        "YouTube helper routes are deferred in this build.",
        success=True,
        Videos=[],
    )


@router.post("/sources/get-document")
async def sources_get_document() -> PlainTextResponse:
    return PlainTextResponse("", status_code=200, headers=deferred_feature_headers("source-document-mirror"))


@router.get("/sources/financial-reports/sec/edgar/{path:path}")
async def sec_document(_: str) -> PlainTextResponse:
    return PlainTextResponse("", status_code=200, headers=deferred_feature_headers("sec-financial-report-mirror"))


@router.get("/sources/financial-reports/sec/edgar-submissions/{path:path}")
async def sec_submissions(_: str) -> PlainTextResponse:
    return PlainTextResponse("", status_code=200, headers=deferred_feature_headers("sec-financial-report-mirror"))
