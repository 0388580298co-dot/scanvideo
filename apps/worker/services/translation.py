from __future__ import annotations

import os
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
    provider = os.getenv("SCANVIDEO_TRANSLATION_PROVIDER", "openai").lower().strip()
    if provider == "passthrough":
        return PassthroughTranslator().translate(segments, target_language)

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is required for translation. Set SCANVIDEO_TRANSLATION_PROVIDER=passthrough "
            "only for local testing."
        )

    from apps.worker.services.openai_translate import OpenAITranslator

    input_segments = [TranslationSegment(s.start, s.end, s.text, "") for s in segments]
    return OpenAITranslator().translate_segments(input_segments, target_language)
