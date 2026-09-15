from pathlib import Path

import pytest

from apps.worker.services.media import MediaError, download_video, normalize_source_url


def test_normalize_douyin_modal_url() -> None:
    url = "https://www.douyin.com/jingxuan?modal_id=7677584450095549705"
    assert normalize_source_url(url) == "https://www.douyin.com/video/7677584450095549705"


def test_normalize_non_douyin_url_unchanged() -> None:
    url = "https://www.youtube.com/watch?v=abc123"
    assert normalize_source_url(url) == url


def test_download_uses_canonical_douyin_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **kwargs):
        calls.append(command)
        (tmp_path / "source.mp4").write_bytes(b"video")
        return type("Result", (), {"returncode": 0, "stderr": "", "stdout": ""})()

    monkeypatch.delenv("DOUYIN_COOKIE_FILE", raising=False)
    monkeypatch.setattr("apps.worker.services.media.subprocess.run", fake_run)

    result = download_video(
        "https://www.douyin.com/jingxuan?modal_id=7677584450095549705",
        tmp_path,
    )

    assert result == tmp_path / "source.mp4"
    command = calls[0]
    assert command[-1] == "https://www.douyin.com/video/7677584450095549705"
    assert "--add-header" in command
    assert "Referer: https://www.douyin.com/" in command
    assert "--cookies" not in command


def test_download_adds_optional_douyin_cookie_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **kwargs):
        calls.append(command)
        (tmp_path / "source.mp4").write_bytes(b"video")
        return type("Result", (), {"returncode": 0, "stderr": "", "stdout": ""})()

    monkeypatch.setenv("DOUYIN_COOKIE_FILE", "/secrets/douyin.cookies.txt")
    monkeypatch.setattr("apps.worker.services.media.subprocess.run", fake_run)

    download_video("https://www.douyin.com/video/7677584450095549705", tmp_path)

    command = calls[0]
    assert command[command.index("--cookies") + 1] == "/secrets/douyin.cookies.txt"


def test_download_falls_back_to_browser_for_douyin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_run(command: list[str], **kwargs):
        return type(
            "Result",
            (),
            {
                "returncode": 1,
                "stderr": "ERROR: Failed to parse JSON: Expecting value in ''",
                "stdout": "",
            },
        )()

    expected = tmp_path / "source.mp4"
    expected.write_bytes(b"browser-video")
    monkeypatch.delenv("DOUYIN_COOKIE_FILE", raising=False)
    monkeypatch.setattr("apps.worker.services.media.subprocess.run", fake_run)
    monkeypatch.setattr(
        "apps.worker.services.media._browser_download_douyin",
        lambda *args, **kwargs: expected,
    )

    result = download_video("https://www.douyin.com/video/7677584450095549705", tmp_path)

    assert result == expected


def test_download_reports_browser_fallback_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_run(command: list[str], **kwargs):
        return type(
            "Result",
            (),
            {
                "returncode": 1,
                "stderr": "ERROR: Fresh cookies (not necessarily logged in) are needed",
                "stdout": "",
            },
        )()

    monkeypatch.delenv("DOUYIN_COOKIE_FILE", raising=False)
    monkeypatch.setattr("apps.worker.services.media.subprocess.run", fake_run)
    monkeypatch.setattr(
        "apps.worker.services.media._browser_download_douyin",
        lambda *args, **kwargs: (_ for _ in ()).throw(MediaError("browser could not expose video source")),
    )

    with pytest.raises(MediaError, match="browser could not expose video source"):
        download_video("https://www.douyin.com/video/7677584450095549705", tmp_path)
