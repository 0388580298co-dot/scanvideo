from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from apps.worker.services.transcription import TranscriptSegment


class TranslationError(RuntimeError):
    """Raised when the configured translation provider cannot translate safely."""


@dataclass(slots=True)
class TranslationSegment:
    start: float
    end: float
    source_text: str
    translated_text: str


class Translator(Protocol):
    def translate(self, segments: list[TranscriptSegment], target_language: str) -> list[TranslationSegment]: ...


def _validate_output(segments: list[TranslationSegment]) -> list[TranslationSegment]:
    previous_end = -1.0
    validated: list[TranslationSegment] = []
    for segment in segments:
        if segment.start < 0 or segment.end <= segment.start:
            raise TranslationError("Translator returned invalid segment timing")
        if segment.start < previous_end - 0.05:
            raise TranslationError("Translator returned overlapping segments")
        if not segment.translated_text.strip():
            raise TranslationError("Translator returned an empty translation")
        validated.append(segment)
        previous_end = segment.end
    return validated


class ArgosTranslator:
    """Offline Argos Translate adapter. Models must be installed locally."""

    def translate(self, segments: list[TranscriptSegment], target_language: str) -> list[TranslationSegment]:
        try:
            import argostranslate.translate as argos
        except ImportError as exc:
            raise TranslationError(
                "Argos Translate is not installed. Install the translation dependency and an "
                "English-to-Vietnamese Argos model before running the pipeline."
            ) from exc

        translated: list[TranslationSegment] = []
        for segment in segments:
            try:
                text = argos.translate(segment.text, "en", target_language)
            except Exception as exc:
                raise TranslationError(f"Argos translation failed: {exc}") from exc
            translated.append(TranslationSegment(segment.start, segment.end, segment.text, text))
        return _validate_output(translated)


def _cache_key(segments: list[TranscriptSegment], target_language: str) -> str:
    payload = [{"s": s.start, "e": s.end, "t": s.text} for s in segments]
    raw = json.dumps([target_language, payload], ensure_ascii=False, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()


def translate_segments(
    segments: list[TranscriptSegment],
    target_language: str,
    cache_path: Path | None = None,
) -> list[TranslationSegment]:
    if not segments:
        raise TranslationError("No transcript segments to translate")
    if target_language != "vi":
        raise TranslationError(f"Unsupported target language for the local MVP: {target_language}")

    key = _cache_key(segments, target_language)
    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        if cache_path.exists():
            try:
                payload = json.loads(cache_path.read_text(encoding="utf-8"))
                if payload.get("cache_key") == key:
                    return _validate_output([TranslationSegment(**item) for item in payload["segments"]])
            except (OSError, ValueError, TypeError, KeyError):
                pass

    from apps.api.core.config import settings

    provider = settings.translation_provider.lower().strip()
    if provider != "argos":
        raise TranslationError(
            f"Unknown translation provider '{provider}'. Supported local provider: argos."
        )
    result = ArgosTranslator().translate(segments, target_language)

    if cache_path is not None:
        cache_path.write_text(
            json.dumps({"cache_key": key, "segments": [asdict(s) for s in result]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return result
