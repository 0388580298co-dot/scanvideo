from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class PublishRequest:
    job_id: str
    platform: str
    media_path: str
    title: str
    description: str = ""
    scheduled_at: datetime | None = None


class PublishingQueue:
    """Small persistence-agnostic queue boundary; storage can be swapped for DB later."""

    def __init__(self) -> None:
        self._items: list[PublishRequest] = []

    def enqueue(self, request: PublishRequest) -> PublishRequest:
        self._items.append(request)
        return request

    def due(self, now: datetime) -> list[PublishRequest]:
        return [x for x in self._items if x.scheduled_at is None or x.scheduled_at <= now]


publishing_queue = PublishingQueue()
