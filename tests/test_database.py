from apps.api.db.base import Base
from apps.api.db.models import Job, PublishedPost, ScheduledPost


def test_core_database_models_are_registered():
    expected = {
        "users", "jobs", "source_media", "transcripts", "translations", "tts_segments",
        "rendered_media", "platform_accounts", "scheduled_posts", "published_posts", "trend_items",
    }
    assert expected.issubset(Base.metadata.tables)


def test_job_primary_key_is_string():
    assert Job.__table__.c.id.type.length == 64


def test_platform_publish_foreign_keys_exist():
    assert any(fk.target_fullname == "platform_accounts.id" for fk in ScheduledPost.__table__.c.platform_account_id.foreign_keys)
    assert any(fk.target_fullname == "scheduled_posts.id" for fk in PublishedPost.__table__.c.scheduled_post_id.foreign_keys)
