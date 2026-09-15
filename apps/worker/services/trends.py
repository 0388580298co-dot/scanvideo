from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class TrendItem:
    title: str
    source_url: str
    score: float = 0.0
    source: str = "unknown"


class TrendProvider(Protocol):
    def discover(self, limit: int = 20) -> list[TrendItem]: ...


class ConfiguredFeedTrendProvider:
    """Provider boundary for an authorized/official trend feed.

    The service deliberately does not bypass CAPTCHAs, bot protection, login walls,
    or other access controls. Point it at a feed/API integration that you are
    authorized to use, then map its results to TrendItem.
    """

    def __init__(self, items: list[TrendItem] | None = None) -> None:
        self.items = items or []

    def discover(self, limit: int = 20) -> list[TrendItem]:
        return sorted(self.items, key=lambda item: item.score, reverse=True)[:limit]
