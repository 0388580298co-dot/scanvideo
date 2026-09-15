from __future__ import annotations

from pathlib import Path

from apps.worker.services.translation import TranslationSegment


def _timestamp(seconds: float) -> str:
    milliseconds = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt(segments: list[TranslationSegment], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    blocks: list[str] = []
    for index, segment in enumerate(segments, start=1):
        blocks.append(
            f"{index}\n{_timestamp(segment.start)} --> {_timestamp(segment.end)}\n"
            f"{segment.translated_text.strip()}\n"
        )
    path.write_text("\n".join(blocks), encoding="utf-8")
    return path
