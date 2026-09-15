from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


class MediaError(RuntimeError):
    """Raised for download, probing, validation, or media-processing failures."""


def download_video(url: str, output_dir: Path, min_duration: float = 10.0, max_duration: float = 180.0) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    template = str(output_dir / "source.%(ext)s")
    duration_filter = f"duration >= {min_duration} & duration <= {max_duration}"
    command = [
        "yt-dlp", "--no-playlist", "--merge-output-format", "mp4",
        "--match-filter", duration_filter,
        "-f", "bv*+ba/b", "-o", template, url,
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=900)
    if result.returncode != 0:
        raise MediaError(result.stderr[-3000:] or "yt-dlp failed or source duration was outside the allowed range")
    candidates = sorted(
        p for p in output_dir.glob("source.*") if p.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}
    )
    if not candidates:
        raise MediaError("Download completed but no video file was produced; source may be outside duration limits")
    return candidates[0]


def probe_video(path: Path) -> dict:
    if not path.exists() or path.stat().st_size == 0:
        raise MediaError("Media file is missing or empty")
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        raise MediaError(result.stderr[-3000:] or "ffprobe failed")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise MediaError("ffprobe returned invalid JSON") from exc


def validate_video(path: Path, min_duration: float, max_duration: float) -> dict:
    metadata = probe_video(path)
    duration = float(metadata.get("format", {}).get("duration") or 0)
    streams = metadata.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    if video_stream is None:
        raise MediaError("Source has no video stream")
    if not has_audio:
        raise MediaError("Source has no audio stream")
    if duration < min_duration:
        raise MediaError(f"Video is too short: {duration:.2f}s < {min_duration:.2f}s")
    if duration > max_duration:
        raise MediaError(f"Video is too long: {duration:.2f}s > {max_duration:.2f}s")
    return {
        "duration": duration,
        "width": int(video_stream.get("width") or 0),
        "height": int(video_stream.get("height") or 0),
        "has_audio": has_audio,
        "video_codec": video_stream.get("codec_name", ""),
        "format": metadata.get("format", {}).get("format_name", ""),
    }


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()
