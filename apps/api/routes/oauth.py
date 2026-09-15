from __future__ import annotations

import json
import secrets
from pathlib import Path
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from apps.api.core.config import settings
from apps.api.db.base import SessionLocal
from apps.api.db.models import PlatformAccount

router = APIRouter(prefix="/api/v1/oauth", tags=["oauth"])
STATE_DIR = settings.secret_root / "oauth"


def _state_file(platform: str) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / f"{platform}_state"


def _save_state(platform: str, state: str) -> None:
    _state_file(platform).write_text(state, encoding="utf-8")


def _consume_state(platform: str, state: str) -> None:
    path = _state_file(platform)
    expected = path.read_text(encoding="utf-8") if path.exists() else ""
    if not expected or not secrets.compare_digest(expected, state):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    path.unlink(missing_ok=True)


def _ensure_account(platform: str, name: str, credential_ref: str) -> None:
    with SessionLocal() as session:
        row = session.scalar(select(PlatformAccount).where(PlatformAccount.platform == platform).order_by(PlatformAccount.id).limit(1))
        if row is None:
            session.add(PlatformAccount(platform=platform, account_name=name, credential_ref=credential_ref, enabled=True))
        else:
            row.account_name = name
            row.credential_ref = credential_ref
            row.enabled = True
        session.commit()


@router.get("/youtube/start")
def youtube_start() -> RedirectResponse:
    try:
        from google_auth_oauthlib.flow import Flow
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="Install the publishing extra first") from exc
    if not settings.youtube_client_secrets_file.exists():
        raise HTTPException(status_code=503, detail="YouTube client_secret.json is not configured")
    flow = Flow.from_client_secrets_file(str(settings.youtube_client_secrets_file), scopes=["https://www.googleapis.com/auth/youtube.upload"], redirect_uri="http://localhost:8000/api/v1/oauth/youtube/callback")
    state = secrets.token_urlsafe(32)
    _save_state("youtube", state)
    url, _ = flow.authorization_url(access_type="offline", include_granted_scopes="true", state=state, prompt="consent")
    return RedirectResponse(url)


@router.get("/youtube/callback")
def youtube_callback(code: str = Query(...), state: str = Query(...)) -> dict:
    _consume_state("youtube", state)
    try:
        from google_auth_oauthlib.flow import Flow
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="Install the publishing extra first") from exc
    flow = Flow.from_client_secrets_file(str(settings.youtube_client_secrets_file), scopes=["https://www.googleapis.com/auth/youtube.upload"], redirect_uri="http://localhost:8000/api/v1/oauth/youtube/callback")
    flow.fetch_token(code=code)
    settings.youtube_token_file.parent.mkdir(parents=True, exist_ok=True)
    settings.youtube_token_file.write_text(flow.credentials.to_json(), encoding="utf-8")
    _ensure_account("youtube", "YouTube OAuth account", str(settings.youtube_token_file))
    return {"status": "connected", "platform": "youtube", "message": "OAuth completed; token stored outside the repository"}


@router.get("/tiktok/start")
def tiktok_start() -> RedirectResponse:
    if not settings.tiktok_client_key or not settings.tiktok_client_secret:
        raise HTTPException(status_code=503, detail="TikTok client key/secret is not configured")
    state = secrets.token_urlsafe(32)
    _save_state("tiktok", state)
    params = {"client_key": settings.tiktok_client_key, "response_type": "code", "scope": "user.info.basic,video.publish", "redirect_uri": settings.tiktok_redirect_uri, "state": state}
    return RedirectResponse("https://www.tiktok.com/v2/auth/authorize/?" + urlencode(params))


@router.get("/tiktok/callback")
def tiktok_callback(code: str = Query(...), state: str = Query(...)) -> dict:
    _consume_state("tiktok", state)
    response = requests.post("https://open.tiktokapis.com/v2/oauth/token/", headers={"Content-Type": "application/x-www-form-urlencoded"}, data={"client_key": settings.tiktok_client_key, "client_secret": settings.tiktok_client_secret, "code": code, "grant_type": "authorization_code", "redirect_uri": settings.tiktok_redirect_uri}, timeout=30)
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="TikTok OAuth token exchange failed")
    payload = response.json()
    token_path = settings.secret_root / "oauth" / "tiktok_token.json"
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    _ensure_account("tiktok", "TikTok OAuth account", str(token_path))
    return {"status": "connected", "platform": "tiktok", "message": "OAuth completed; tokens stored outside the repository"}
