from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from apps.worker.services.transcription import TranscriptSegment


@dataclass(slots=True)
class TranslationSegment:
    start: float
    end: float
    source_text: str
    translated_text: str


class Translator(Protocol):
    def translate(self, segments: list[TranscriptSegment], target_language: str) -> list[TranslationSegment]: ...


class PassthroughTranslator:
    """Deterministic fallback used when no external translation provider is configured."""

    def translate(self, segments: list[TranscriptSegment], target_language: str) -> list[TranslationSegment]:
        return [
            TranslationSegment(s.start, s.end, s.text, s.text)
            for s in segments
        ]


def translate_segments(segments: list[TranscriptSegment], target_language: str) -> list[TranslationSegment]:
    return PassthroughTranslator().translate(segments, target_language)
