"""Add scheduling metadata and nullable account selection support.

Revision ID: 0002_scheduled_post_metadata
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_scheduled_post_metadata"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scheduled_posts", sa.Column("platform", sa.String(32), nullable=True))
    op.add_column("scheduled_posts", sa.Column("title", sa.String(2200), nullable=True))
    op.add_column("scheduled_posts", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("scheduled_posts", sa.Column("privacy_level", sa.String(64), nullable=True))
    op.add_column("scheduled_posts", sa.Column("error", sa.Text(), nullable=True))
    op.execute("UPDATE scheduled_posts SET platform = 'youtube', title = '', description = '', privacy_level = 'private'")
    op.alter_column("scheduled_posts", "platform", nullable=False)
    op.alter_column("scheduled_posts", "title", nullable=False)
    op.alter_column("scheduled_posts", "description", nullable=False)
    op.alter_column("scheduled_posts", "privacy_level", nullable=False)
    op.create_index("ix_scheduled_posts_platform", "scheduled_posts", ["platform"])


def downgrade() -> None:
    op.drop_index("ix_scheduled_posts_platform", table_name="scheduled_posts")
    for column in ["error", "privacy_level", "description", "title", "platform"]:
        op.drop_column("scheduled_posts", column)
