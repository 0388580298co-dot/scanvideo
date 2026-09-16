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
    """Normalize source URLs that yt-dlp cannot consume directly."""
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


def _probe_has_audio(path: Path) -> bool:
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "a:0",
                "-show_entries", "stream=codec_type", "-of", "json", str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return False
        payload = json.loads(result.stdout or "{}")
        return bool(payload.get("streams"))
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return False


def _browser_download_douyin(
    url: str, output_dir: Path, min_duration: float, max_duration: float
) -> Path:
    """Use a normal browser page as a Douyin fallback when yt-dlp cannot extract it.

    Some Douyin pages expose a video-only HTML5 source while audio is requested as a
    separate media resource. We capture public audio responses from the same browser
    page and mux one into the video when necessary. This does not solve CAPTCHAs,
    bypass access controls, or evade rate limits.
    """
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise MediaError(
            "Douyin không tải được bằng yt-dlp và Playwright chưa được cài trong worker."
        ) from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / "source.mp4"
    browser_video = output_dir / ".douyin-browser-video.mp4"
    audio_candidates: list[str] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
                    ),
                    extra_http_headers={"Referer": "https://www.douyin.com/"},
                )
                page = context.new_page()
                media_responses: list[tuple[str, str]] = []

                def capture_media(response) -> None:
                    content_type = response.headers.get("content-type", "").lower()
                    if content_type.startswith("audio/") or content_type.startswith("video/"):
                        media_responses.append((response.url, content_type))

                page.on("response", capture_media)
                page.goto(url, wait_until="domcontentloaded", timeout=45_000)
                page.wait_for_function(
                    "() => Array.from(document.querySelectorAll('video')).some(v => v.currentSrc || v.src)",
                    timeout=30_000,
                )
                page.wait_for_timeout(3000)

                video_info = page.locator("video").evaluate_all(
                    """els => els.flatMap(v => [
                        {src: v.currentSrc || v.src, duration: v.duration},
                        ...Array.from(v.querySelectorAll('source[src]')).map(s => ({src: s.src, duration: v.duration}))
                    ]).filter(x => x.src && !x.src.startsWith('blob:'))"""
                )
                if not video_info:
                    raise MediaError("Douyin page không cung cấp video source công khai cho trình duyệt.")

                info = next((item for item in video_info if item.get("src")), video_info[0])
                duration = float(info.get("duration") or 0)
                if duration and (duration < min_duration or duration > max_duration):
                    raise MediaError(
                        f"Video is outside duration limits: {duration:.2f}s "
                        f"(allowed {min_duration:.2f}-{max_duration:.2f}s)"
                    )

                video_url = str(info["src"])
                response = context.request.get(
                    video_url,
                    headers={"Referer": "https://www.douyin.com/"},
                    timeout=120_000,
                )
                if not response.ok:
                    raise MediaError(f"Douyin video source returned HTTP {response.status}")
                browser_video.write_bytes(response.body())

                if _probe_has_audio(browser_video):
                    browser_video.replace(target)
                    return target

                dom_audio = page.locator("audio").evaluate_all(
                    """els => els.flatMap(a => [
                        a.currentSrc || a.src,
                        ...Array.from(a.querySelectorAll('source[src]')).map(s => s.src)
                    ]).filter(Boolean).filter(x => !x.startsWith('blob:'))"""
                )
                for audio_url in [*dom_audio, *[u for u, ct in media_responses if ct.startswith("audio/")]]:
                    if audio_url and audio_url not in audio_candidates and audio_url != video_url:
                        audio_candidates.append(audio_url)

                for index, audio_url in enumerate(audio_candidates[:12]):
                    try:
                        audio_response = context.request.get(
                            audio_url,
                            headers={"Referer": "https://www.douyin.com/"},
                            timeout=60_000,
                        )
                        if not audio_response.ok:
                            continue
                        audio_path = output_dir / f".douyin-browser-audio-{index}"
                        audio_path.write_bytes(audio_response.body())
                        if not _probe_has_audio(audio_path):
                            audio_path.unlink(missing_ok=True)
                            continue

                        mux = subprocess.run(
                            [
                                "ffmpeg", "-y", "-v", "error",
                                "-i", str(browser_video), "-i", str(audio_path),
                                "-map", "0:v:0", "-map", "1:a:0",
                                "-c:v", "copy", "-c:a", "aac", "-shortest", str(target),
                            ],
                            capture_output=True,
                            text=True,
                            timeout=180,
                        )
                        audio_path.unlink(missing_ok=True)
                        if mux.returncode == 0 and target.exists() and _probe_has_audio(target):
                            return target
                    except (OSError, subprocess.SubprocessError):
                        continue
            finally:
                browser.close()
    except PlaywrightTimeoutError as exc:
        raise MediaError("Douyin page timed out while waiting for its video source.") from exc
    except MediaError:
        raise
    except Exception as exc:
        raise MediaError(f"Douyin browser fallback failed: {exc}") from exc
    finally:
        browser_video.unlink(missing_ok=True)
        for path in output_dir.glob(".douyin-browser-audio-*"):
            path.unlink(missing_ok=True)

    raise MediaError(
        "Douyin browser fallback chỉ lấy được video không có audio; "
        "trang không cung cấp audio resource công khai có thể tải trực tiếp."
    )


def download_video(
    url: str, output_dir: Path, min_duration: float = 10.0, max_duration: float = 180.0
) -> Path:
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
    is_douyin = _is_douyin_url(source_url)
    if is_douyin:
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
        if is_douyin:
            if "Unsupported URL" in detail or "Fresh cookies" in detail or "Failed to parse JSON" in detail:
                try:
                    return _browser_download_douyin(source_url, output_dir, min_duration, max_duration)
                except MediaError as browser_exc:
                    raise MediaError(
                        f"Douyin yt-dlp failed: {detail.strip()}\nBrowser fallback: {browser_exc}"
                    ) from browser_exc
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
