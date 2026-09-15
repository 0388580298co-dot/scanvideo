from apps.api.db.base import Base
from apps.api.db.models import Job, PublishAttempt, PublishedPost, ScheduledPost


def test_core_database_models_are_registered():
    expected = {
        "users", "jobs", "source_media", "transcripts", "translations", "tts_segments",
        "rendered_media", "platform_accounts", "scheduled_posts", "publish_attempts", "published_posts", "trend_items",
    }
    assert expected.issubset(Base.metadata.tables)


def test_job_primary_key_is_string():
    assert Job.__table__.c.id.type.length == 64


def test_platform_publish_foreign_keys_exist():
    assert any(fk.target_fullname == "platform_accounts.id" for fk in ScheduledPost.__table__.c.platform_account_id.foreign_keys)
    assert any(fk.target_fullname == "scheduled_posts.id" for fk in PublishedPost.__table__.c.scheduled_post_id.foreign_keys)
    assert any(fk.target_fullname == "scheduled_posts.id" for fk in PublishAttempt.__table__.c.scheduled_post_id.foreign_keys)


def test_publish_attempt_is_unique_per_scheduled_post():
    column = PublishAttempt.__table__.c.scheduled_post_id
    assert column.unique is True
    assert any(
        constraint.name == "uq_publish_attempt_scheduled_post"
        for constraint in PublishAttempt.__table__.constraints
    )
