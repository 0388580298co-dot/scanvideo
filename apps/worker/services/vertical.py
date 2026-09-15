from __future__ import annotations

import subprocess
from pathlib import Path

from apps.worker.services.media import MediaError


def render_vertical(source: Path, output: Path, width: int = 1080, height: int = 1920) -> Path:
    """Create a vertical master using aspect-preserving scale + center crop."""
    if width <= 0 or height <= 0:
        raise MediaError("Output dimensions must be positive")
    output.parent.mkdir(parents=True, exist_ok=True)
    vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(source), "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output)],
        capture_output=True, text=True, timeout=900,
    )
    if result.returncode != 0:
        raise MediaError(result.stderr[-4000:] or "Vertical render failed")
    if not output.exists() or output.stat().st_size < 1024:
        raise MediaError("Vertical render produced no valid output")
    return output
