from __future__ import annotations

from pathlib import Path


class YouTubePublisher:
    """OAuth-backed publisher boundary. Credentials are intentionally supplied at runtime."""

    def __init__(self, credentials_file: Path, token_file: Path) -> None:
        self.credentials_file = credentials_file
        self.token_file = token_file

    def upload(self, video_path: Path, title: str, description: str = "", privacy: str = "private") -> dict:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        scopes = ["https://www.googleapis.com/auth/youtube.upload"]
        creds = None
        if self.token_file.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_file), scopes)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_file), scopes)
                creds = flow.run_local_server(port=0)
            self.token_file.write_text(creds.to_json(), encoding="utf-8")

        youtube = build("youtube", "v3", credentials=creds)
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {"title": title[:100], "description": description},
                "status": {"privacyStatus": privacy},
            },
            media_body=MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True),
        )
        response = None
        while response is None:
            _, response = request.next_chunk()
        return response
