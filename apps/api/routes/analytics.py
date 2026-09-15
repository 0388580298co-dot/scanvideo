from __future__ import annotations

from sqlalchemy import func, select
from fastapi import APIRouter, HTTPException, Query

from apps.api.db.base import SessionLocal
from apps.api.db.models import PublishedPost
from apps.worker.services.analytics import AnalyticsError, refresh_metrics

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/summary")
def summary() -> dict:
    with SessionLocal() as session:
        rows = session.execute(
            select(PublishedPost.platform, func.count(PublishedPost.id)).group_by(PublishedPost.platform)
        ).all()
        return {
            "published_total": sum(count for _, count in rows),
            "by_platform": {platform: count for platform, count in rows},
        }


@router.get("/published")
def published(limit: int = Query(default=100, ge=1, le=500)) -> list[dict]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(PublishedPost).order_by(PublishedPost.published_at.desc()).limit(limit)
        ).all()
        return [
            {
                "id": row.id,
                "platform": row.platform,
                "external_id": row.external_id,
                "published_at": row.published_at,
                "metrics": row.metrics,
            }
            for row in rows
        ]


@router.post("/published/{published_id}/refresh")
def refresh_published(published_id: int) -> dict:
    with SessionLocal() as session:
        row = session.get(PublishedPost, published_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Published post not found")
        platform = row.platform
        external_id = row.external_id
    try:
        metrics = refresh_metrics(platform, external_id)
    except AnalyticsError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    with SessionLocal() as session:
        row = session.get(PublishedPost, published_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Published post not found")
        row.metrics = metrics
        session.commit()
        return {"id": row.id, "platform": row.platform, "external_id": row.external_id, "metrics": row.metrics}
