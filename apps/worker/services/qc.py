from __future__ import annotations

import subprocess
from pathlib import Path

from apps.worker.services.media import MediaError, probe_video


def quality_gate(path: Path, expected_min_duration: float = 1.0, expected_width: int = 1080, expected_height: int = 1920) -> dict:
    if not path.exists() or path.stat().st_size == 0:
        raise MediaError("QC failed: output file is missing or empty")
    metadata = probe_video(path)
    duration = float(metadata.get("format", {}).get("duration") or 0)
    streams = metadata.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if video is None:
        raise MediaError("QC failed: output has no video stream")
    if audio is None:
        raise MediaError("QC failed: output has no audio stream")
    width = int(video.get("width") or 0)
    height = int(video.get("height") or 0)
    if (width, height) != (expected_width, expected_height):
        raise MediaError(f"QC failed: expected {expected_width}x{expected_height}, got {width}x{height}")
    if duration < expected_min_duration:
        raise MediaError("QC failed: output duration is invalid")

    decode = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"],
        capture_output=True, text=True, timeout=600,
    )
    if decode.returncode != 0:
        raise MediaError(f"QC failed: decode check failed: {decode.stderr[-2000:]}")

    return {"passed": True, "duration": duration, "width": width, "height": height, "has_video": True, "has_audio": True, "size_bytes": path.stat().st_size}
