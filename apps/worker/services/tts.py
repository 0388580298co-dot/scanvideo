from __future__ import annotations

import subprocess
from pathlib import Path

from apps.worker.services.media import MediaError
from apps.worker.services.translation import TranslationSegment


class TTSProvider:
    """Provider boundary for Vietnamese TTS."""

    def synthesize(self, text: str, output_path: Path, language: str = "vi") -> Path:
        raise NotImplementedError


class EdgeTTSProvider(TTSProvider):
    """Simple configurable provider. Use only voices you are authorized to use."""

    def __init__(self, voice: str = "vi-VN-HoaiMyNeural", rate: str = "+0%") -> None:
        self.voice = voice
        self.rate = rate

    def synthesize(self, text: str, output_path: Path, language: str = "vi") -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["edge-tts", "--voice", self.voice, "--rate", self.rate, "--text", text, "--write-media", str(output_path)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise MediaError(result.stderr[-4000:] or "edge-tts failed")
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise MediaError("TTS produced no audio")
        return output_path


def fit_audio_to_duration(source: Path, output: Path, duration: float) -> Path:
    """Fit a synthesized clip into its speech window without changing pitch."""
    if duration <= 0:
        raise MediaError("TTS target duration must be positive")
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(source)],
        capture_output=True, text=True,
    )
    if probe.returncode != 0:
        raise MediaError("Unable to probe TTS duration")
    try:
        actual = float(probe.stdout.strip() or 0)
    except ValueError as exc:
        raise MediaError("Invalid TTS duration returned by ffprobe") from exc
    if actual <= 0:
        raise MediaError("Invalid TTS duration")
    ratio = actual / duration
    filters: list[str] = []
    value = ratio
    while value > 2.0:
        filters.append("atempo=2.0")
        value /= 2.0
    while value < 0.5:
        filters.append("atempo=0.5")
        value /= 0.5
    filters.append(f"atempo={value}")
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(source), "-filter:a", ",".join(filters), "-t", f"{duration:.3f}", "-ac", "2", "-ar", "48000", str(output)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise MediaError(result.stderr[-4000:] or "Unable to fit TTS audio")
    if not output.exists() or output.stat().st_size == 0:
        raise MediaError("TTS fitting produced no audio")
    return output


def synthesize_segments(
    provider: TTSProvider,
    segments: list[TranslationSegment],
    output_dir: Path,
) -> list[Path]:
    """Synthesize segments resumably; valid existing artifacts are reused."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for index, segment in enumerate(segments):
        raw = output_dir / f"tts_{index:04d}.mp3"
        fitted = output_dir / f"tts_{index:04d}_fit.wav"
        if not raw.exists() or raw.stat().st_size == 0:
            provider.synthesize(segment.translated_text, raw)
        if not fitted.exists() or fitted.stat().st_size == 0:
            fit_audio_to_duration(raw, fitted, segment.end - segment.start)
        paths.append(fitted)
    return paths
