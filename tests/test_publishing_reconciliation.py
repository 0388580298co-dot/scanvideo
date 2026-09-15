from __future__ import annotations

import apps.worker.tasks.publishing as publishing
from sqlalchemy.exc import IntegrityError


class FakeAttempt:
    def __init__(self, external_id="publish-123"):
        self.external_id = external_id
        self.provider_status = None
        self.status = "SUBMITTED"
        self.error = None
        self.updated_at = None


class FakeQuery:
    def __init__(self, value):
        self.value = value

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.value


class FakeSession:
    def __init__(self, attempt):
        self.attempt = attempt

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def query(self, model):
        return FakeQuery(self.attempt)

    def commit(self):
        pass


def test_tiktok_terminal_failure_never_returns_for_reupload(monkeypatch):
    attempt = FakeAttempt()
    session = FakeSession(attempt)

    class Provider:
        def publish_status(self, publish_id):
            return {"data": {"status": "FAILED"}}

    monkeypatch.setattr(publishing, "SessionLocal", lambda: session)
    monkeypatch.setattr(publishing, "_snapshot", lambda session, post_id: (
        "job-1", "tiktok", "title", "description", "SELF_ONLY", "/tmp/video.mp4",
        1, "tiktok", "account", "token.json"
    ))
    monkeypatch.setattr(publishing, "_publisher", lambda account, platform: Provider())

    try:
        publishing._reconcile_existing(1)
    except publishing.PublishTerminalError:
        pass
    else:
        raise AssertionError("terminal provider failure must not be treated as a missing submission")

    assert attempt.status == "FAILED"
    assert "FAILED" in attempt.error


def test_tiktok_processing_state_is_retryable(monkeypatch):
    attempt = FakeAttempt()
    session = FakeSession(attempt)

    class Provider:
        def publish_status(self, publish_id):
            return {"data": {"status": "PROCESSING_UPLOAD"}}

    monkeypatch.setattr(publishing, "SessionLocal", lambda: session)
    monkeypatch.setattr(publishing, "_snapshot", lambda session, post_id: (
        "job-1", "tiktok", "title", "description", "SELF_ONLY", "/tmp/video.mp4",
        1, "tiktok", "account", "token.json"
    ))
    monkeypatch.setattr(publishing, "_publisher", lambda account, platform: Provider())

    try:
        publishing._reconcile_existing(1)
    except ConnectionError:
        pass
    else:
        raise AssertionError("processing provider state must remain retryable")

    assert attempt.provider_status == "PROCESSING_UPLOAD"


def test_publish_attempt_claim_race_is_not_a_failure():
    """A unique-constraint race means another worker owns the post, not that publishing failed."""

    class RaceSession:
        def __init__(self):
            self.added = None
            self.rolled_back = False
            self.commits = 0

        def query(self, model):
            return FakeQuery(None)

        def add(self, value):
            self.added = value

        def commit(self):
            self.commits += 1
            raise IntegrityError("INSERT", {}, Exception("duplicate scheduled post"))

        def rollback(self):
            self.rolled_back = True

    session = RaceSession()
    claimed = publishing._claim_publish_attempt(session, 42, "tiktok")

    assert claimed is None
    assert session.rolled_back is True
    assert session.commits == 1
    assert session.added.scheduled_post_id == 42
    assert session.added.platform == "tiktok"
