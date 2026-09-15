from __future__ import annotations

import subprocess
from pathlib import Path

from apps.worker.services.media import MediaError


def render_subtitles(source: Path, subtitles: Path, output: Path) -> Path:
    """Render subtitles onto the source while preserving its original audio."""
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-y", "-i", str(source), "-vf", f"subtitles={subtitles}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise MediaError(result.stderr[-4000:] or "FFmpeg render failed")
    if not output.exists() or output.stat().st_size == 0:
        raise MediaError("FFmpeg completed without producing an output file")
    return output
