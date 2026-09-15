from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from apps.api.db.base import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_url: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), index=True)
    target_language: Mapped[str] = mapped_column(String(10), default="vi")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(Text, default="")
    output_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    auto_publish: Mapped[bool] = mapped_column(Boolean, default=False)
    content_package: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class SourceMedia(Base):
    __tablename__ = "source_media"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    source_url: Mapped[str] = mapped_column(Text)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    path: Mapped[str] = mapped_column(Text)
    duration: Mapped[float] = mapped_column(Float)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Transcript(Base):
    __tablename__ = "transcripts"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), unique=True)
    source_language: Mapped[str] = mapped_column(String(16))
    segments: Mapped[list] = mapped_column(JSON)


class Translation(Base):
    __tablename__ = "translations"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), unique=True)
    source_language: Mapped[str] = mapped_column(String(16))
    target_language: Mapped[str] = mapped_column(String(16))
    segments: Mapped[list] = mapped_column(JSON)


class TtsSegment(Base):
    __tablename__ = "tts_segments"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    segment_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    start: Mapped[float] = mapped_column(Float)
    end: Mapped[float] = mapped_column(Float)
    path: Mapped[str] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("job_id", "segment_index", name="uq_tts_job_segment"),)


class RenderedMedia(Base):
    __tablename__ = "rendered_media"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    path: Mapped[str] = mapped_column(Text)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    duration: Mapped[float] = mapped_column(Float)
    qc_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    qc: Mapped[dict] = mapped_column(JSON, default=dict)


class PlatformAccount(Base):
    __tablename__ = "platform_accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    account_name: Mapped[str] = mapped_column(String(160))
    credential_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class ScheduledPost(Base):
    __tablename__ = "scheduled_posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    platform_account_id: Mapped[int] = mapped_column(ForeignKey("platform_accounts.id", ondelete="CASCADE"))
    platform: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(2200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    privacy_level: Mapped[str] = mapped_column(String(64), default="SELF_ONLY")
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(32), default="SCHEDULED", index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class PublishAttempt(Base):
    __tablename__ = "publish_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    scheduled_post_id: Mapped[int] = mapped_column(ForeignKey("scheduled_posts.id", ondelete="CASCADE"), unique=True, index=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), default="STARTED", index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    provider_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class PublishedPost(Base):
    __tablename__ = "published_posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    scheduled_post_id: Mapped[int | None] = mapped_column(ForeignKey("scheduled_posts.id", ondelete="SET NULL"), nullable=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)


class TrendItem(Base):
    __tablename__ = "trend_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text, unique=True)
    score: Mapped[float] = mapped_column(Float, default=0)
    source: Mapped[str] = mapped_column(String(64))
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
