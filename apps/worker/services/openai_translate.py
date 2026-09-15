from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from apps.worker.services.translation import TranslationSegment


class OpenAITranslationError(RuntimeError):
    pass


class OpenAITranslator:
    def __init__(self, api_key: str | None = None, model: str = "gpt-5-mini") -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        if not self.api_key:
            raise OpenAITranslationError("OPENAI_API_KEY is not configured")

    def translate_segments(self, segments: list[TranslationSegment], target_language: str = "vi") -> list[TranslationSegment]:
        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": "Translate each segment naturally for Vietnamese short-form narration. Preserve meaning. Return JSON only with key translations, an array of strings in the exact input order."
                },
                {
                    "role": "user",
                    "content": json.dumps({"target_language": target_language, "segments": [s.source_text for s in segments]}, ensure_ascii=False)
                },
            ],
            "text": {"format": {"type": "json_object"}},
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            raise OpenAITranslationError(f"OpenAI translation request failed: {exc}") from exc

        text = data.get("output_text")
        if not text:
            raise OpenAITranslationError("OpenAI returned no output_text")
        try:
            result = json.loads(text)
            translations = result["translations"]
        except (ValueError, KeyError, TypeError) as exc:
            raise OpenAITranslationError("OpenAI returned invalid translation JSON") from exc
        if len(translations) != len(segments):
            raise OpenAITranslationError("Translation count does not match transcript count")
        return [TranslationSegment(s.start, s.end, s.source_text, str(t).strip()) for s, t in zip(segments, translations)]
