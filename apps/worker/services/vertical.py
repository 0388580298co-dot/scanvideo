from __future__ import annotations

import subprocess
from pathlib import Path

from apps.worker.services.media import MediaError


def render_vertical(source: Path, output: Path) -> Path:
    """Create a 1080x1920 vertical master with a center crop for landscape input."""
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-y", "-i", str(source),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise MediaError(result.stderr[-4000:] or "Vertical render failed")
    if not output.exists() or output.stat().st_size < 1024:
        raise MediaError("Vertical render produced no valid output")
    return output
