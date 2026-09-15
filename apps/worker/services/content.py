from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(slots=True)
class ContentPackage:
    title: str
    description: str
    hashtags: list[str]


class ContentGenerator:
    """Generate short-form metadata without changing the source transcript."""

    def __init__(self, api_key: str | None = None, model: str = "gpt-5-mini") -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model

    def generate(self, transcript: str, language: str = "vi") -> ContentPackage:
        if not self.api_key:
            return ContentPackage(
                title="Video ngắn đáng xem",
                description=transcript[:500],
                hashtags=["#shorts", "#viral", "#xuhuong"],
            )
        payload = {
            "model": self.model,
            "input": [
                {"role": "system", "content": "Create concise Vietnamese short-video metadata. Return JSON only: title, description, hashtags. Do not invent facts."},
                {"role": "user", "content": json.dumps({"language": language, "transcript": transcript}, ensure_ascii=False)},
            ],
            "text": {"format": {"type": "json_object"}},
        }
        req = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                data = json.loads(response.read().decode())
            obj = json.loads(data["output_text"])
            hashtags = [str(x) for x in obj.get("hashtags", [])][:8]
            return ContentPackage(str(obj["title"]).strip(), str(obj["description"]).strip(), hashtags)
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError, ValueError, TypeError) as exc:
            raise RuntimeError(f"Content generation failed: {exc}") from exc
