from sqlalchemy import func, select
from fastapi import APIRouter

from apps.api.db.base import SessionLocal
from apps.api.db.models import PublishedPost

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/summary")
def summary() -> dict:
    with SessionLocal() as session:
        rows = session.execute(select(PublishedPost.platform, func.count(PublishedPost.id)).group_by(PublishedPost.platform)).all()
        return {"published_total": sum(count for _, count in rows), "by_platform": {platform: count for platform, count in rows}}


@router.get("/published")
def published() -> list[dict]:
    with SessionLocal() as session:
        rows = session.scalars(select(PublishedPost).order_by(PublishedPost.published_at.desc())).all()
        return [{"id": row.id, "platform": row.platform, "external_id": row.external_id, "published_at": row.published_at, "metrics": row.metrics} for row in rows]
