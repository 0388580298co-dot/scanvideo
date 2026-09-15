from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True)
class TranscriptSegment:
    start: float
    end: float
    text: str


class WhisperTranscriber:
    """Lazy-loaded faster-whisper adapter with automatic CPU/CUDA selection."""

    def __init__(self, model_size: str = "small", device: str = "auto", compute_type: str = "auto") -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None
        self.detected_language: str | None = None

    def _load(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            device = self.device
            if device == "auto":
                try:
                    import torch
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                except ImportError:
                    device = "cpu"
            compute_type = self.compute_type
            if compute_type == "auto":
                compute_type = "float16" if device == "cuda" else "int8"
            self._model = WhisperModel(self.model_size, device=device, compute_type=compute_type)
        return self._model

    def transcribe(self, media_path: Path, language: str | None = None) -> list[TranscriptSegment]:
        model = self._load()
        segments, info = model.transcribe(
            str(media_path),
            language=language,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
            condition_on_previous_text=False,
            beam_size=5,
            temperature=0.0,
        )
        self.detected_language = getattr(info, "language", None)
        return [
            TranscriptSegment(float(s.start), float(s.end), s.text.strip())
            for s in segments
            if s.text.strip() and float(s.end) > float(s.start) >= 0
        ]


def save_transcript(segments: list[TranscriptSegment], path: Path, language: str | None = None) -> None:
    import json
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"language": language, "segments": [asdict(s) for s in segments]}, ensure_ascii=False, indent=2), encoding="utf-8")
