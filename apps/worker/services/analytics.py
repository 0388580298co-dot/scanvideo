from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class AnalyticsError(RuntimeError):
    pass


def _youtube_client():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    token_file = Path(os.getenv("YOUTUBE_TOKEN_FILE", "/secrets/youtube_token.json"))
    if not token_file.exists():
        raise AnalyticsError("YouTube OAuth token is missing")
    scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
    creds = Credentials.from_authorized_user_file(str(token_file), scopes)
    if not creds.valid:
        raise AnalyticsError("YouTube OAuth token is expired or invalid")
    return build("youtube", "v3", credentials=creds)


def youtube_metrics(video_id: str) -> dict[str, Any]:
    if not video_id:
        raise AnalyticsError("YouTube video id is required")
    youtube = _youtube_client()
    response = youtube.videos().list(part="statistics", id=video_id).execute()
    items = response.get("items", [])
    if not items:
        raise AnalyticsError("YouTube video was not found")
    stats = items[0].get("statistics", {})
    return {
        "views": int(stats.get("viewCount", 0)),
        "likes": int(stats.get("likeCount", 0)),
        "comments": int(stats.get("commentCount", 0)),
        "source": "youtube_data_api_v3",
    }


def refresh_metrics(platform: str, external_id: str | None) -> dict[str, Any]:
    """Fetch metrics only from an official provider; never invent unavailable metrics."""
    if platform == "youtube":
        return youtube_metrics(external_id or "")
    if platform == "tiktok":
        raise AnalyticsError("TikTok metrics provider is not available in the current official API adapter")
    raise AnalyticsError(f"Unsupported analytics platform: {platform}")
