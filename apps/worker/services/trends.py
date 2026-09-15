from __future__ import annotations

from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Protocol
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

import requests


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


class RssTrendProvider:
    """Read public RSS/Atom feeds configured by the operator.

    The provider never accepts arbitrary feed URLs from HTTP requests, which
    avoids turning the API into an SSRF proxy. Feed URLs come from settings.
    """

    def __init__(self, feed_urls: list[str] | None = None, timeout: float = 10.0) -> None:
        self.feed_urls = [url for url in (feed_urls or []) if self._is_http_url(url)]
        self.timeout = timeout

    @staticmethod
    def _is_http_url(url: str) -> bool:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    def discover(self, limit: int = 20) -> list[TrendItem]:
        items: list[TrendItem] = []
        for feed_url in self.feed_urls:
            try:
                response = requests.get(
                    feed_url,
                    timeout=self.timeout,
                    headers={"User-Agent": "ScanVideo/0.4 (+RSS trend reader)"},
                )
                response.raise_for_status()
                items.extend(self._parse(response.content, feed_url))
            except requests.RequestException:
                continue
        return rank_trends(items)[:limit]

    @staticmethod
    def _parse(payload: bytes, feed_url: str) -> list[TrendItem]:
        root = ET.fromstring(payload)
        source = urlparse(feed_url).netloc or "rss"
        items: list[TrendItem] = []
        for node in root.iter():
            if node.tag.rsplit("}", 1)[-1] not in {"item", "entry"}:
                continue
            fields = {
                child.tag.rsplit("}", 1)[-1]: (child.text or "").strip()
                for child in node
            }
            title = fields.get("title", "").strip()
            link = fields.get("link", "").strip()
            if not link:
                for child in node:
                    if child.tag.rsplit("}", 1)[-1] == "link":
                        link = child.attrib.get("href", "").strip()
                        if link:
                            break
            if not title or not link or not RssTrendProvider._is_http_url(link):
                continue
            score = RssTrendProvider._score(fields)
            items.append(TrendItem(title=title[:500], source_url=link, score=score, source=source))
        return items

    @staticmethod
    def _score(fields: dict[str, str]) -> float:
        for key in ("score", "rank", "popularity"):
            value = fields.get(key)
            if value:
                try:
                    number = float(value)
                    return 1.0 / max(number, 1.0) if key == "rank" else number
                except ValueError:
                    pass
        published = fields.get("published") or fields.get("pubDate") or fields.get("updated")
        if published:
            try:
                dt = parsedate_to_datetime(published)
                return dt.timestamp()
            except (TypeError, ValueError, OverflowError):
                pass
        return 0.0


def rank_trends(items: list[TrendItem]) -> list[TrendItem]:
    return sorted(items, key=lambda item: item.score, reverse=True)
