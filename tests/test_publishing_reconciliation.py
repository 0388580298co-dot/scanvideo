from __future__ import annotations

import apps.worker.tasks.publishing as publishing


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
