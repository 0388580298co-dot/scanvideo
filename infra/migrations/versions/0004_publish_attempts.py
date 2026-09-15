"""Persist provider publish identifiers before finalization.

Revision ID: 0004_publish_attempts
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_publish_attempts"
down_revision = "0003_job_content_package"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "publish_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scheduled_post_id", sa.Integer(), sa.ForeignKey("scheduled_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="STARTED"),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("provider_status", sa.String(length=64), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("scheduled_post_id", name="uq_publish_attempt_scheduled_post"),
    )
    op.create_index("ix_publish_attempts_scheduled_post_id", "publish_attempts", ["scheduled_post_id"], unique=True)
    op.create_index("ix_publish_attempts_platform", "publish_attempts", ["platform"])
    op.create_index("ix_publish_attempts_status", "publish_attempts", ["status"])
    op.create_index("ix_publish_attempts_external_id", "publish_attempts", ["external_id"])


def downgrade() -> None:
    op.drop_index("ix_publish_attempts_external_id", table_name="publish_attempts")
    op.drop_index("ix_publish_attempts_status", table_name="publish_attempts")
    op.drop_index("ix_publish_attempts_platform", table_name="publish_attempts")
    op.drop_index("ix_publish_attempts_scheduled_post_id", table_name="publish_attempts")
    op.drop_table("publish_attempts")
