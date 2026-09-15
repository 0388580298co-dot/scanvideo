from __future__ import annotations

from pathlib import Path

from apps.worker.services.media import probe_video, MediaError


def quality_gate(path: Path, expected_min_duration: float = 1.0) -> dict:
    if not path.exists() or path.stat().st_size == 0:
        raise MediaError("QC failed: output file is missing or empty")
    metadata = probe_video(path)
    duration = float(metadata.get("format", {}).get("duration") or 0)
    streams = metadata.get("streams", [])
    has_video = any(s.get("codec_type") == "video" for s in streams)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    if not has_video:
        raise MediaError("QC failed: output has no video stream")
    if duration < expected_min_duration:
        raise MediaError("QC failed: output duration is invalid")
    return {
        "passed": True,
        "duration": duration,
        "has_video": has_video,
        "has_audio": has_audio,
        "size_bytes": path.stat().st_size,
    }
