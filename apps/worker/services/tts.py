from __future__ import annotations

from pathlib import Path

from apps.worker.services.translation import TranslationSegment


class TTSProvider:
    """Provider boundary for Vietnamese TTS. Real providers can implement synthesize()."""

    def synthesize(self, segment: TranslationSegment, output_path: Path) -> Path:
        raise NotImplementedError("Configure a TTS provider before synthesis")


def synthesize_segments(segments: list[TranslationSegment], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    # Do not silently create fake audio. This keeps pipeline output trustworthy.
    raise RuntimeError("TTS provider is not configured")
