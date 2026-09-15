import pytest

from apps.worker.services.audio_mix import mix_narration_with_background
from apps.worker.services.media import MediaError
from apps.worker.services.translation import TranslationSegment


def test_audio_mix_builds_delayed_narration_and_limiter(monkeypatch, tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    narration = tmp_path / "narration.mp3"
    narration.write_bytes(b"narration")
    output = tmp_path / "mixed.mp4"
    calls = []

    class Result:
        returncode = 0
        stderr = ""

    def fake_run(command, **kwargs):
        calls.append(command)
        output.write_bytes(b"mixed")
        return Result()

    monkeypatch.setattr("apps.worker.services.audio_mix.subprocess.run", fake_run)
    segments = [TranslationSegment(start=1.25, end=2.5, text="Xin chào")]

    result = mix_narration_with_background(source, [narration], segments, output)

    assert result == output
    command = " ".join(calls[0])
    assert "adelay=1250:all=1" in command
    assert "volume=-18.0dB" in command
    assert "alimiter=limit=0.95" in command
    assert output.exists()


def test_audio_mix_rejects_mismatched_inputs(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    output = tmp_path / "mixed.mp4"
    segment = TranslationSegment(start=0, end=1, text="Xin chào")

    with pytest.raises(MediaError):
        mix_narration_with_background(source, [], [segment], output)
