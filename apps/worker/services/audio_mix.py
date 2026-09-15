from __future__ import annotations

import subprocess
from pathlib import Path

from apps.worker.services.media import MediaError
from apps.worker.services.translation import TranslationSegment


def mix_narration_with_background(
    source: Path,
    narration_paths: list[Path],
    segments: list[TranslationSegment],
    output: Path,
    narration_gain_db: float = 0.0,
    background_gain_db: float = -18.0,
) -> Path:
    """Mix localized narration into source audio with safe timing and peak limiting."""
    if not source.exists() or not narration_paths or len(narration_paths) != len(segments):
        raise MediaError("Audio mix inputs are missing or inconsistent")
    output.parent.mkdir(parents=True, exist_ok=True)

    inputs = ["-i", str(source)]
    for path in narration_paths:
        if not path.exists() or path.stat().st_size == 0:
            raise MediaError(f"Narration file is missing or empty: {path}")
        inputs.extend(["-i", str(path)])

    filters = [f"[0:a]volume={background_gain_db}dB[bg]"]
    delayed_labels: list[str] = []
    for index, segment in enumerate(segments, start=1):
        delay_ms = max(0, round(segment.start * 1000))
        label = f"n{index}"
        filters.append(
            f"[{index}:a]volume={narration_gain_db}dB,adelay={delay_ms}:all=1[{label}]"
        )
        delayed_labels.append(f"[{label}]")

    mix_inputs = "[bg]" + "".join(delayed_labels)
    filters.append(
        f"{mix_inputs}amix=inputs={len(delayed_labels) + 1}:duration=first:dropout_transition=0:normalize=0," 
        "alimiter=limit=0.95:level_in=1:level_out=1[aout]"
    )
    command = [
        "ffmpeg",
        "-y",
        *inputs,
        "-filter_complex",
        ";".join(filters),
        "-map",
        "0:v?",
        "-map",
        "[aout]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(output),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise MediaError(result.stderr[-4000:] or "Narration audio mixing failed")
    if not output.exists() or output.stat().st_size == 0:
        raise MediaError("Narration audio mixing produced no output")
    return output
