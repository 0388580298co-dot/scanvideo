from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path


class YouTubePublisher:
    """Official YouTube Data API v3 uploader using OAuth 2.0 credentials."""

    def __init__(self, credentials_file: Path, token_file: Path) -> None:
        self.credentials_file = credentials_file
        self.token_file = token_file

    def upload(self, video_path: Path, title: str, description: str = "", privacy: str = "private", tags: list[str] | None = None, publish_at: datetime | None = None) -> dict:
        if privacy not in {"private", "unlisted", "public"}:
            raise ValueError("Invalid YouTube privacy status")
        if not video_path.exists() or video_path.stat().st_size == 0:
            raise FileNotFoundError(video_path)
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import Flow
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from apps.api.core.config import settings

        scopes = ["https://www.googleapis.com/auth/youtube.upload"]
        creds = None
        if self.token_file.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_file), scopes)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.credentials_file.exists():
                    raise RuntimeError("YouTube OAuth client_secret.json is missing")
                flow = Flow.from_client_secrets_file(str(self.credentials_file), scopes=scopes)
                flow.redirect_uri = settings.youtube_redirect_uri
                url, _ = flow.authorization_url(access_type="offline", include_granted_scopes="true", prompt="consent")
                raise RuntimeError(f"YouTube OAuth required. Open {url} then retry the publish job.")
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            self.token_file.write_text(creds.to_json(), encoding="utf-8")

        status = {"privacyStatus": privacy}
        if publish_at is not None:
            status["privacyStatus"] = "private"
            status["publishAt"] = publish_at.astimezone().isoformat()
        body = {"snippet": {"title": title[:100], "description": description[:5000], "tags": (tags or [])[:500]}, "status": status}
        youtube = build("youtube", "v3", credentials=creds)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True))
        response = None
        while response is None:
            _, response = request.next_chunk()
        return response
