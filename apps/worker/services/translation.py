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
    def translate(self, segments: list[TranscriptSegment], target_language: str) -> list[TranslationSegment]:
        return [TranslationSegment(s.start, s.end, s.text, s.text) for s in segments]


def translate_segments(segments: list[TranscriptSegment], target_language: str) -> list[TranslationSegment]:
    if target_language.lower() in {"vi", "vie", "vietnamese"}:
        try:
            from apps.worker.services.openai_translate import OpenAITranslator
            return OpenAITranslator().translate_segments(
                [TranslationSegment(s.start, s.end, s.text, "") for s in segments], target_language
            )
        except Exception:
            # Keep local/offline development usable when no provider key is configured.
            pass
    return PassthroughTranslator().translate(segments, target_language)
