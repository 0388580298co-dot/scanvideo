from __future__ import annotations

import math
from pathlib import Path

import requests


API = "https://open.tiktokapis.com/v2"


class TikTokPublisher:
    def __init__(self, access_token: str) -> None:
        self.access_token = access_token

    def creator_info(self) -> dict:
        response = requests.post(
            f"{API}/post/publish/creator_info/query/",
            headers={"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def publish_file(self, video_path: Path, title: str, privacy_level: str = "SELF_ONLY") -> dict:
        size = video_path.stat().st_size
        chunk = min(size, 10_000_000)
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
        upload_url = result.get("data", {}).get("upload_url")
        if upload_url:
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
