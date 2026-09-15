from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from urllib.parse import parse_qs, urlparse


class MediaError(RuntimeError):
    """Raised for download, probing, validation, or media-processing failures."""


def normalize_source_url(url: str) -> str:
    """Normalize source URLs that yt-dlp cannot consume directly.

    Douyin frequently shares videos as ``/jingxuan?modal_id=...`` (and other
    page routes carrying ``modal_id``).  yt-dlp expects the canonical
    ``/video/{id}`` route, so convert those links before invoking it.
    """
    value = url.strip()
    parsed = urlparse(value)
    host = parsed.netloc.lower().split(":", 1)[0]
    if host in {"douyin.com", "www.douyin.com", "m.douyin.com"}:
        modal_id = parse_qs(parsed.query).get("modal_id", [""])[0].strip()
        if modal_id.isdigit():
            return f"https://www.douyin.com/video/{modal_id}"
    return value


def _is_douyin_url(url: str) -> bool:
    host = urlparse(url).netloc.lower().split(":", 1)[0]
    return host in {"douyin.com", "www.douyin.com", "m.douyin.com", "v.douyin.com"}


def download_video(url: str, output_dir: Path, min_duration: float = 10.0, max_duration: float = 180.0) -> Path:
    """Download only sources whose metadata duration is within the configured bounds."""
    output_dir.mkdir(parents=True, exist_ok=True)
    source_url = normalize_source_url(url)
    template = str(output_dir / "source.%(ext)s")
    duration_filter = f"duration >= {min_duration} & duration <= {max_duration}"
    command = [
        "yt-dlp", "--no-playlist", "--merge-output-format", "mp4",
        "--match-filter", duration_filter,
        "-f", "bv*+ba/b", "-o", template,
    ]
    if _is_douyin_url(source_url):
        command.extend(["--add-header", "Referer: https://www.douyin.com/"])
        cookie_file = os.getenv("DOUYIN_COOKIE_FILE", "").strip()
        if cookie_file:
            command.extend(["--cookies", cookie_file])
    command.append(source_url)
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=900)
    except subprocess.TimeoutExpired as exc:
        raise MediaError(f"Video download timed out after 900 seconds: {source_url}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout)[-3000:]
        if _is_douyin_url(source_url) and "Fresh cookies" in detail:
            raise MediaError(
                "Douyin yêu cầu cookie mới để tải video. "
                "Đặt DOUYIN_COOKIE_FILE trỏ tới file cookie của nội dung bạn được phép tải, "
                "hoặc thử một video Douyin công khai khác."
            )
        raise MediaError(detail or "yt-dlp failed or source duration was outside the allowed range")
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
