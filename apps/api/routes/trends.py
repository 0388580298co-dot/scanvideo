from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Query
from sqlalchemy import select

from apps.api.core.config import settings
from apps.api.db.base import SessionLocal
from apps.api.db.models import TrendItem as TrendItemModel
from apps.worker.services.trends import RssTrendProvider, TrendItem

router = APIRouter(prefix="/api/v1/trends", tags=["trends"])


def _provider() -> RssTrendProvider:
    return RssTrendProvider(settings.trend_feed_urls)


@router.get("")
def discover(limit: int = Query(default=20, ge=1, le=100)) -> list[dict]:
    """Discover trends from configured public/authorized RSS feeds and persist them."""
    items = _provider().discover(limit=limit)
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        for item in items:
            existing = session.scalar(select(TrendItemModel).where(TrendItemModel.source_url == item.source_url))
            if existing is None:
                session.add(
                    TrendItemModel(
                        title=item.title,
                        source_url=item.source_url,
                        score=item.score,
                        source=item.source,
                        duration=item.duration,
                        discovered_at=now,
                    )
                )
            else:
                existing.title = item.title
                existing.score = item.score
                existing.source = item.source
                existing.duration = item.duration
                existing.discovered_at = now
        session.commit()
        rows = session.scalars(select(TrendItemModel).order_by(TrendItemModel.score.desc(), TrendItemModel.discovered_at.desc()).limit(limit)).all()
        return [
            {
                "id": row.id,
                "title": row.title,
                "source_url": row.source_url,
                "score": row.score,
                "source": row.source,
                "duration": row.duration,
                "discovered_at": row.discovered_at,
            }
            for row in rows
        ]


@router.get("/stored")
def stored(limit: int = Query(default=50, ge=1, le=200)) -> list[dict]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(TrendItemModel).order_by(TrendItemModel.discovered_at.desc()).limit(limit)
        ).all()
        return [
            {
                "id": row.id,
                "title": row.title,
                "source_url": row.source_url,
                "score": row.score,
                "source": row.source,
                "duration": row.duration,
                "discovered_at": row.discovered_at,
            }
            for row in rows
        ]
