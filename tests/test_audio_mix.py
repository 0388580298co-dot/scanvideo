from pathlib import Path

import pytest

from apps.worker.services.audio_mix import mix_narration_with_background
from apps.worker.services.translation import TranslationSegment


def test_audio_mix_builds_delayed_narration_and_limiter(monkeypatch, tmp_path):
    source = tmp_path / "source.mp4"
    narration = tmp_path / "narration.mp3"
    output = tmp_path / "mixed.mp4"
    source.write_bytes(b"video")
    narration.write_bytes(b"audio")
    captured = {}

    class Result:
        returncode = 0
        stderr = ""

    def fake_run(command, **kwargs):
        captured["command"] = command
        output.write_bytes(b"result")
        return Result()

    monkeypatch.setattr("apps.worker.services.audio_mix.subprocess.run", fake_run)
    segments = [TranslationSegment(start=1.25, end=3.0, translated_text="Xin chào")]
    mix_narration_with_background(source, [narration], segments, output)

    command = captured["command"]
    assert "adelay=1250:all=1" in " ".join(command)
    assert "volume=-18.0dB" in " ".join(command)
    assert "alimiter=limit=0.95" in " ".join(command)
    assert output.exists()


def test_audio_mix_rejects_mismatched_inputs(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"video")
    segment = TranslationSegment(start=0, end=1, translated_text="Xin chào")
    with pytest.raises(Exception):
        mix_narration_with_background(source, [], [segment], tmp_path / "out.mp4")
