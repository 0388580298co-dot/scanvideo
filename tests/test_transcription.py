from pathlib import Path
from types import SimpleNamespace

from apps.worker.services.transcription import WhisperTranscriber


class FakeModel:
    def transcribe(self, path, **kwargs):
        assert Path(path).name == "audio.wav"
        assert kwargs["vad_filter"] is True
        assert kwargs["condition_on_previous_text"] is False
        return [
            SimpleNamespace(start=0.0, end=1.2, text=" Hello "),
            SimpleNamespace(start=2.0, end=2.0, text="invalid"),
            SimpleNamespace(start=-1.0, end=0.5, text="invalid"),
            SimpleNamespace(start=3.0, end=4.0, text="   "),
            SimpleNamespace(start=4.0, end=5.5, text="World"),
        ], SimpleNamespace(language="vi")


def test_transcribe_filters_invalid_segments(tmp_path):
    transcriber = WhisperTranscriber()
    transcriber._model = FakeModel()

    segments = transcriber.transcribe(tmp_path / "audio.wav")

    assert [(s.start, s.end, s.text) for s in segments] == [
        (0.0, 1.2, "Hello"),
        (4.0, 5.5, "World"),
    ]
    assert transcriber.detected_language == "vi"
