from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import requests


API = "https://open.tiktokapis.com/v2"
TOKEN_URL = f"{API}/oauth/token/"


class TikTokPublisher:
    def __init__(
        self,
        access_token: str | None = None,
        token_file: Path | None = None,
        client_key: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        self.token_file = token_file or Path(os.getenv("TIKTOK_TOKEN_FILE", "./.secrets/oauth/tiktok_token.json"))
        self.access_token = access_token or os.getenv("TIKTOK_ACCESS_TOKEN", "")
        self.client_key = client_key or os.getenv("TIKTOK_CLIENT_KEY", "")
        self.client_secret = client_secret or os.getenv("TIKTOK_CLIENT_SECRET", "")
        self._token_payload: dict = {}
        if self.token_file.exists():
            self._token_payload = json.loads(self.token_file.read_text(encoding="utf-8"))
            self.access_token = self.access_token or self._token_payload.get("access_token", "")
        self._refresh_if_needed()
        if not self.access_token:
            raise RuntimeError("TikTok access token is not configured")

    def _refresh_if_needed(self) -> None:
        expires_at = self._token_payload.get("expires_at")
        refresh_token = self._token_payload.get("refresh_token", "")
        if not refresh_token or not self.client_key or not self.client_secret or not expires_at:
            return
        try:
            expiry = float(expires_at)
        except (TypeError, ValueError):
            return
        if expiry - datetime.now(timezone.utc).timestamp() > 300:
            return
        response = requests.post(
            TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "client_key": self.client_key,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        error = payload.get("error")
        if error and error not in ("", "ok"):
            raise RuntimeError(payload.get("error_description", f"TikTok token refresh failed: {error}"))
        data = payload.get("data", payload)
        new_access = data.get("access_token")
        if not new_access:
            raise RuntimeError("TikTok token refresh returned no access token")
        self.access_token = new_access
        self._token_payload.update(data)
        expires_in = data.get("expires_in")
        if expires_in is not None:
            self._token_payload["expires_at"] = datetime.now(timezone.utc).timestamp() + float(expires_in)
        if self.token_file:
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            self.token_file.write_text(json.dumps(self._token_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def creator_info(self) -> dict:
        response = requests.post(
            f"{API}/post/publish/creator_info/query/",
            headers={"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        error = payload.get("error", {})
        if error.get("code") not in (None, "ok"):
            raise RuntimeError(error.get("message", "TikTok creator info query failed"))
        return payload.get("data", payload)

    def publish_status(self, publish_id: str) -> dict:
        if not publish_id:
            raise ValueError("publish_id is required")
        response = requests.post(
            f"{API}/post/publish/status/fetch/",
            headers={"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"},
            json={"publish_id": publish_id},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        error = payload.get("error", {})
        if error.get("code") not in (None, "ok"):
            raise RuntimeError(error.get("message", "TikTok publish status query failed"))
        return payload

    def publish_file(self, video_path: Path, title: str, privacy_level: str | None = None) -> dict:
        if not video_path.exists() or video_path.stat().st_size == 0:
            raise RuntimeError("TikTok upload file is missing or empty")

        creator = self.creator_info()
        privacy_options = creator.get("privacy_level_options") or []
        if not privacy_options:
            raise RuntimeError("TikTok returned no available privacy levels")
        if privacy_level is None:
            raise ValueError("TikTok privacy_level must be explicitly selected")
        if privacy_level not in privacy_options:
            raise ValueError(f"TikTok privacy level is not available: {privacy_level}")

        size = video_path.stat().st_size
        chunk = size if size <= 5_000_000 else min(size, 10_000_000)
        total = max(1, math.ceil(size / chunk))
        payload = {
            "post_info": {"title": title[:2200], "privacy_level": privacy_level},
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": size,
                "chunk_size": chunk,
                "total_chunk_count": total,
            },
        }
        response = requests.post(
            f"{API}/post/publish/video/init/",
            headers={"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        if result.get("error", {}).get("code") not in (None, "ok"):
            raise RuntimeError(result.get("error", {}).get("message", "TikTok publish initialization failed"))
        upload_url = result.get("data", {}).get("upload_url")
        publish_id = result.get("data", {}).get("publish_id")
        if not upload_url or not publish_id:
            raise RuntimeError("TikTok publish initialization returned no upload URL or publish ID")

        with video_path.open("rb") as handle:
            offset = 0
            while offset < size:
                data = handle.read(chunk)
                end = offset + len(data) - 1
                upload = requests.put(
                    upload_url,
                    headers={
                        "Content-Type": "video/mp4",
                        "Content-Length": str(len(data)),
                        "Content-Range": f"bytes {offset}-{end}/{size}",
                    },
                    data=data,
                    timeout=120,
                )
                upload.raise_for_status()
                offset += len(data)
        return result
