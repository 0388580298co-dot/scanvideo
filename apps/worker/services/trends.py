from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class TrendItem:
    title: str
    source_url: str
    score: float = 0.0
    source: str = "unknown"
    duration: float | None = None


class TrendProvider(Protocol):
    def discover(self, limit: int = 20) -> list[TrendItem]: ...


class ConfiguredFeedTrendProvider:
    """Adapter boundary for an authorized or official trend feed."""

    def __init__(self, items: list[TrendItem] | None = None) -> None:
        self.items = items or []

    def discover(self, limit: int = 20) -> list[TrendItem]:
        return rank_trends(self.items)[:limit]


def rank_trends(items: list[TrendItem]) -> list[TrendItem]:
    return sorted(items, key=lambda item: item.score, reverse=True)
