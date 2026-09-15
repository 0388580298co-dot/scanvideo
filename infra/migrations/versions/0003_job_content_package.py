"""Persist deterministic content package.

Revision ID: 0003_job_content_package
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_job_content_package"
down_revision = "0002_scheduled_post_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("content_package", sa.JSON(), nullable=True))
    op.execute("UPDATE jobs SET content_package = '{}' WHERE content_package IS NULL")
    op.alter_column("jobs", "content_package", nullable=False)


def downgrade() -> None:
    op.drop_column("jobs", "content_package")
