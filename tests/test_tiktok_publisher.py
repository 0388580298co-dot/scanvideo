from pathlib import Path

import pytest

from apps.worker.services.publishers.tiktok import TikTokPublisher


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self._payload = payload or {"error": {"code": "ok"}}
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_tiktok_requires_explicit_available_privacy(monkeypatch, tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")
    publisher = TikTokPublisher(access_token="token", token_file=tmp_path / "missing.json")
    monkeypatch.setattr(publisher, "creator_info", lambda: {"privacy_level_options": ["SELF_ONLY", "PUBLIC_TO_EVERYONE"]})

    with pytest.raises(ValueError, match="must be explicitly selected"):
        publisher.publish_file(video, "test")
    with pytest.raises(ValueError, match="not available"):
        publisher.publish_file(video, "test", "FOLLOWER_OF_CREATOR")


def test_tiktok_rejects_video_above_creator_duration_limit(monkeypatch, tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")
    publisher = TikTokPublisher(access_token="token", token_file=tmp_path / "missing.json")
    monkeypatch.setattr(
        publisher,
        "creator_info",
        lambda: {"privacy_level_options": ["SELF_ONLY"], "max_video_post_duration_sec": 30},
    )
    monkeypatch.setattr(
        "apps.worker.services.publishers.tiktok.probe_video",
        lambda _: {"format": {"duration": "30.2"}},
    )

    with pytest.raises(ValueError, match="exceeds TikTok creator limit"):
        publisher.publish_file(video, "test", "SELF_ONLY")


def test_tiktok_allows_video_within_creator_duration_limit(monkeypatch, tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")
    publisher = TikTokPublisher(access_token="token", token_file=tmp_path / "missing.json")
    monkeypatch.setattr(
        publisher,
        "creator_info",
        lambda: {"privacy_level_options": ["SELF_ONLY"], "max_video_post_duration_sec": 30},
    )
    monkeypatch.setattr(
        "apps.worker.services.publishers.tiktok.probe_video",
        lambda _: {"format": {"duration": "29.9"}},
    )
    monkeypatch.setattr(
        "apps.worker.services.publishers.tiktok.requests.post",
        lambda *args, **kwargs: FakeResponse(
            {"data": {"publish_id": "pub-123", "upload_url": "https://upload.test"}, "error": {"code": "ok"}}
        ),
    )
    monkeypatch.setattr(
        "apps.worker.services.publishers.tiktok.requests.put",
        lambda *args, **kwargs: FakeResponse(),
    )

    result = publisher.publish_file(video, "test", "SELF_ONLY")
    assert result["data"]["publish_id"] == "pub-123"


def test_tiktok_publish_uses_creator_privacy_and_returns_publish_id(monkeypatch, tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video-data")
    publisher = TikTokPublisher(access_token="token", token_file=tmp_path / "missing.json")
    monkeypatch.setattr(publisher, "creator_info", lambda: {"privacy_level_options": ["SELF_ONLY"]})
    calls = []

    def fake_post(url, **kwargs):
        calls.append(("post", url, kwargs))
        return FakeResponse({"data": {"publish_id": "pub-123", "upload_url": "https://upload.test"}, "error": {"code": "ok"}})

    def fake_put(url, **kwargs):
        calls.append(("put", url, kwargs))
        return FakeResponse()

    monkeypatch.setattr("apps.worker.services.publishers.tiktok.requests.post", fake_post)
    monkeypatch.setattr("apps.worker.services.publishers.tiktok.requests.put", fake_put)

    result = publisher.publish_file(video, "test", "SELF_ONLY")
    assert result["data"]["publish_id"] == "pub-123"
    assert calls[0][2]["json"]["post_info"]["privacy_level"] == "SELF_ONLY"
    assert calls[1][0] == "put"


def test_tiktok_publish_status(monkeypatch, tmp_path):
    publisher = TikTokPublisher(access_token="token", token_file=tmp_path / "missing.json")
    monkeypatch.setattr(
        "apps.worker.services.publishers.tiktok.requests.post",
        lambda *args, **kwargs: FakeResponse({"data": {"status": "PUBLISH_COMPLETE"}, "error": {"code": "ok"}}),
    )
    result = publisher.publish_status("pub-123")
    assert result["data"]["status"] == "PUBLISH_COMPLETE"
