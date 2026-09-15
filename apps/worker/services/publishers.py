from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path


class PublisherError(RuntimeError):
    pass


class YouTubePublisher:
    """Official-API adapter boundary. OAuth token handling belongs in deployment secrets."""

    def __init__(self, access_token: str | None = None) -> None:
        self.access_token = access_token or os.getenv("YOUTUBE_ACCESS_TOKEN")
        if not self.access_token:
            raise PublisherError("YOUTUBE_ACCESS_TOKEN is not configured")

    def metadata_only_check(self, title: str, description: str) -> dict:
        return {"platform": "youtube", "ready": True, "title": title[:100], "description": description}


class TikTokPublisher:
    """Official Content Posting API adapter boundary."""

    def __init__(self, access_token: str | None = None) -> None:
        self.access_token = access_token or os.getenv("TIKTOK_ACCESS_TOKEN")
        if not self.access_token:
            raise PublisherError("TIKTOK_ACCESS_TOKEN is not configured")

    def creator_info_url(self) -> str:
        return "https://open.tiktokapis.com/v2/post/publish/creator_info/query/"

    def metadata_only_check(self, title: str) -> dict:
        return {"platform": "tiktok", "ready": True, "title": title[:2200]}
