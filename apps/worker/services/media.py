from __future__ import annotations

import json
import subprocess
from pathlib import Path


class MediaError(RuntimeError):
    pass


def download_video(url: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    template = str(output_dir / "source.%(ext)s")
    command = [
        "yt-dlp",
        "--no-playlist",
        "--merge-output-format", "mp4",
        "-f", "bv*+ba/b",
        "-o", template,
        url,
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise MediaError(result.stderr[-3000:] or "yt-dlp failed")

    candidates = sorted(output_dir.glob("source.*"))
    candidates = [p for p in candidates if p.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}]
    if not candidates:
        raise MediaError("Download completed but no video file was produced")
    return candidates[0]


def probe_video(path: Path) -> dict:
    command = [
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise MediaError(result.stderr[-3000:] or "ffprobe failed")
    return json.loads(result.stdout)


def validate_video(path: Path, min_duration: float, max_duration: float) -> dict:
    metadata = probe_video(path)
    duration = float(metadata.get("format", {}).get("duration") or 0)
    streams = metadata.get("streams", [])
    has_video = any(s.get("codec_type") == "video" for s in streams)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)

    if not has_video:
        raise MediaError("Source has no video stream")
    if not has_audio:
        raise MediaError("Source has no audio stream")
    if duration < min_duration:
        raise MediaError(f"Video is too short: {duration:.2f}s < {min_duration:.2f}s")
    if duration > max_duration:
        raise MediaError(f"Video is too long: {duration:.2f}s > {max_duration:.2f}s")

    video_stream = next(s for s in streams if s.get("codec_type") == "video")
    return {
        "duration": duration,
        "width": int(video_stream.get("width") or 0),
        "height": int(video_stream.get("height") or 0),
        "has_audio": has_audio,
        "format": metadata.get("format", {}).get("format_name", ""),
    }
