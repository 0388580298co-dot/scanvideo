from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json


@dataclass(slots=True)
class ScheduledPost:
    job_id: str
    platform: str
    publish_at: str
    video_path: str
    title: str = ""
    description: str = ""
    hashtags: list[str] | None = None
    status: str = "scheduled"

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "platform": self.platform,
            "publish_at": self.publish_at,
            "video_path": self.video_path,
            "title": self.title,
            "description": self.description,
            "hashtags": self.hashtags or [],
            "status": self.status,
        }


class FileScheduler:
    """Durable local queue used until a database scheduler is enabled."""

    def __init__(self, root: Path) -> None:
        self.path = root / "schedule.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def list(self) -> list[ScheduledPost]:
        if not self.path.exists():
            return []
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return [ScheduledPost(**item) for item in data]

    def add(self, post: ScheduledPost) -> ScheduledPost:
        posts = self.list()
        posts.append(post)
        self.path.write_text(json.dumps([p.to_dict() for p in posts], ensure_ascii=False, indent=2), encoding="utf-8")
        return post

    def due(self, now: datetime | None = None) -> list[ScheduledPost]:
        current = now or datetime.now(timezone.utc)
        return [p for p in self.list() if p.status == "scheduled" and datetime.fromisoformat(p.publish_at) <= current]
