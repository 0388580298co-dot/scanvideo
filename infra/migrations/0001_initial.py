"""Initial ScanVideo schema.

Revision ID: 0001_initial
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("username", sa.String(120), nullable=False, unique=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_users_username", "users", ["username"])
    op.create_table("jobs", sa.Column("id", sa.String(64), primary_key=True), sa.Column("source_url", sa.Text(), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("target_language", sa.String(10), nullable=False), sa.Column("progress", sa.Integer(), nullable=False), sa.Column("message", sa.Text(), nullable=False), sa.Column("output_path", sa.Text()), sa.Column("error", sa.Text()), sa.Column("auto_publish", sa.Boolean(), nullable=False), sa.Column("content_package", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_created_at", "jobs", ["created_at"])
    op.create_table("source_media", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("job_id", sa.String(64), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False), sa.Column("source_url", sa.Text(), nullable=False), sa.Column("fingerprint", sa.String(64), nullable=False, unique=True), sa.Column("path", sa.Text(), nullable=False), sa.Column("duration", sa.Float(), nullable=False), sa.Column("width", sa.Integer(), nullable=False), sa.Column("height", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_source_media_job_id", "source_media", ["job_id"])
    op.create_table("transcripts", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("job_id", sa.String(64), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("source_language", sa.String(16), nullable=False), sa.Column("segments", sa.JSON(), nullable=False))
    op.create_table("translations", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("job_id", sa.String(64), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("source_language", sa.String(16), nullable=False), sa.Column("target_language", sa.String(16), nullable=False), sa.Column("segments", sa.JSON(), nullable=False))
    op.create_table("tts_segments", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("job_id", sa.String(64), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False), sa.Column("segment_index", sa.Integer(), nullable=False), sa.Column("text", sa.Text(), nullable=False), sa.Column("start", sa.Float(), nullable=False), sa.Column("end", sa.Float(), nullable=False), sa.Column("path", sa.Text(), nullable=False), sa.UniqueConstraint("job_id", "segment_index", name="uq_tts_job_segment"))
    op.create_index("ix_tts_segments_job_id", "tts_segments", ["job_id"])
    op.create_table("rendered_media", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("job_id", sa.String(64), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False), sa.Column("path", sa.Text(), nullable=False), sa.Column("width", sa.Integer(), nullable=False), sa.Column("height", sa.Integer(), nullable=False), sa.Column("duration", sa.Float(), nullable=False), sa.Column("qc_passed", sa.Boolean(), nullable=False), sa.Column("qc", sa.JSON(), nullable=False))
    op.create_index("ix_rendered_media_job_id", "rendered_media", ["job_id"])
    op.create_table("platform_accounts", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("platform", sa.String(32), nullable=False), sa.Column("account_name", sa.String(160), nullable=False), sa.Column("credential_ref", sa.String(255)), sa.Column("enabled", sa.Boolean(), nullable=False))
    op.create_index("ix_platform_accounts_platform", "platform_accounts", ["platform"])
    op.create_table("scheduled_posts", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("job_id", sa.String(64), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False), sa.Column("platform_account_id", sa.Integer(), sa.ForeignKey("platform_accounts.id", ondelete="CASCADE"), nullable=False), sa.Column("platform", sa.String(32), nullable=False), sa.Column("title", sa.String(2200), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("privacy_level", sa.String(64), nullable=False), sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("error", sa.Text()))
    op.create_index("ix_scheduled_posts_job_id", "scheduled_posts", ["job_id"])
    op.create_index("ix_scheduled_posts_platform", "scheduled_posts", ["platform"])
    op.create_index("ix_scheduled_posts_scheduled_at", "scheduled_posts", ["scheduled_at"])
    op.create_index("ix_scheduled_posts_status", "scheduled_posts", ["status"])
    op.create_table("published_posts", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("scheduled_post_id", sa.Integer(), sa.ForeignKey("scheduled_posts.id", ondelete="SET NULL")), sa.Column("platform", sa.String(32), nullable=False), sa.Column("external_id", sa.String(255)), sa.Column("published_at", sa.DateTime(timezone=True)), sa.Column("metrics", sa.JSON(), nullable=False))
    op.create_index("ix_published_posts_platform", "published_posts", ["platform"])
    op.create_table("trend_items", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("title", sa.Text(), nullable=False), sa.Column("source_url", sa.Text(), nullable=False, unique=True), sa.Column("score", sa.Float(), nullable=False), sa.Column("source", sa.String(64), nullable=False), sa.Column("duration", sa.Float()), sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_trend_items_discovered_at", "trend_items", ["discovered_at"])


def downgrade() -> None:
    for table in ("trend_items", "published_posts", "scheduled_posts", "platform_accounts", "rendered_media", "tts_segments", "translations", "transcripts", "source_media", "jobs"):
        op.drop_table(table)
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
