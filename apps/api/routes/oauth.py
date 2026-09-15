from __future__ import annotations

import json
import os
import secrets
import tempfile
import time
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
STATE_TTL_SECONDS = 10 * 60


def _state_file(platform: str, state: str) -> Path:
    """Return a per-flow state file so concurrent OAuth flows cannot overwrite each other."""
    safe_state = "".join(ch for ch in state if ch.isalnum() or ch in "-_")
    if not safe_state or safe_state != state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    return STATE_DIR / f"{platform}_{safe_state}.state"


def _atomic_write(path: Path, content: str) -> None:
    """Write credentials/state atomically so a crash cannot leave a truncated secret file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def _save_state(platform: str, state: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    _atomic_write(
        _state_file(platform, state),
        json.dumps({"state": state, "created_at": time.time()}),
    )


def _consume_state(platform: str, state: str) -> None:
    """Validate, expire, and consume exactly one OAuth flow without affecting other flows."""
    path = _state_file(platform, state)
    try:
        payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, json.JSONDecodeError):
        payload = {}

    try:
        created_at = float(payload.get("created_at", 0))
    except (TypeError, ValueError):
        created_at = 0

    expected = payload.get("state", "")
    expired = not created_at or time.time() - created_at > STATE_TTL_SECONDS
    valid = isinstance(expected, str) and secrets.compare_digest(expected, state) and not expired
    path.unlink(missing_ok=True)
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")


def _ensure_account(platform: str, name: str, credential_ref: str) -> None:
    with SessionLocal() as session:
        row = session.scalar(
            select(PlatformAccount)
            .where(PlatformAccount.platform == platform)
            .order_by(PlatformAccount.id)
            .limit(1)
        )
        if row is None:
            session.add(
                PlatformAccount(
                    platform=platform,
                    account_name=name,
                    credential_ref=credential_ref,
                    enabled=True,
                )
            )
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
    flow = Flow.from_client_secrets_file(
        str(settings.youtube_client_secrets_file),
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
        redirect_uri=settings.youtube_redirect_uri,
    )
    state = secrets.token_urlsafe(32)
    _save_state("youtube", state)
    url, _ = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", state=state, prompt="consent"
    )
    return RedirectResponse(url)


@router.get("/youtube/callback")
def youtube_callback(code: str = Query(...), state: str = Query(...)) -> dict:
    _consume_state("youtube", state)
    try:
        from google_auth_oauthlib.flow import Flow
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="Install the publishing extra first") from exc
    flow = Flow.from_client_secrets_file(
        str(settings.youtube_client_secrets_file),
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
        redirect_uri=settings.youtube_redirect_uri,
    )
    flow.fetch_token(code=code)
    _atomic_write(settings.youtube_token_file, flow.credentials.to_json())
    _ensure_account("youtube", "YouTube OAuth account", str(settings.youtube_token_file))
    return {
        "status": "connected",
        "platform": "youtube",
        "message": "OAuth completed; token stored outside the repository",
    }


@router.get("/tiktok/start")
def tiktok_start() -> RedirectResponse:
    if not settings.tiktok_client_key or not settings.tiktok_client_secret:
        raise HTTPException(status_code=503, detail="TikTok client key/secret is not configured")
    state = secrets.token_urlsafe(32)
    _save_state("tiktok", state)
    params = {
        "client_key": settings.tiktok_client_key,
        "response_type": "code",
        "scope": "user.info.basic,video.publish",
        "redirect_uri": settings.tiktok_redirect_uri,
        "state": state,
    }
    return RedirectResponse("https://www.tiktok.com/v2/auth/authorize/?" + urlencode(params))


@router.get("/tiktok/callback")
def tiktok_callback(code: str = Query(...), state: str = Query(...)) -> dict:
    _consume_state("tiktok", state)
    response = requests.post(
        "https://open.tiktokapis.com/v2/oauth/token/",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": settings.tiktok_client_key,
            "client_secret": settings.tiktok_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.tiktok_redirect_uri,
        },
        timeout=30,
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="TikTok OAuth token exchange failed")
    try:
        payload = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="TikTok OAuth returned invalid JSON") from exc
    token_path = settings.secret_root / "oauth" / "tiktok_token.json"
    _atomic_write(token_path, json.dumps(payload, ensure_ascii=False))
    _ensure_account("tiktok", "TikTok OAuth account", str(token_path))
    return {
        "status": "connected",
        "platform": "tiktok",
        "message": "OAuth completed; tokens stored outside the repository",
    }
