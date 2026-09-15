from __future__ import annotations

import subprocess
from pathlib import Path

from apps.worker.services.media import MediaError
from apps.worker.services.translation import TranslationSegment


def extract_audio(source: Path, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = ["ffmpeg", "-y", "-i", str(source), "-vn", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", str(output)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise MediaError(result.stderr[-4000:] or "Audio extraction failed")
    return output


def validate_segments(segments: list[TranslationSegment]) -> None:
    previous_end = 0.0
    for segment in segments:
        if segment.start < 0 or segment.end <= segment.start:
            raise MediaError("Invalid speech segment timing")
        if segment.start < previous_end - 0.02:
            raise MediaError("Overlapping speech segments detected")
        previous_end = segment.end


def build_tts_manifest(segments: list[TranslationSegment], path: Path) -> Path:
    """Persist timing requirements before synthesis so each TTS clip can be fitted safely."""
    import json
    validate_segments(segments)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "index": i,
            "start": s.start,
            "end": s.end,
            "duration": round(s.end - s.start, 3),
            "text": s.translated_text,
        }
        for i, s in enumerate(segments)
    ]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
