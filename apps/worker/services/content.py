from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class ContentPackage:
    title: str
    description: str
    hashtags: list[str]
    hook: str = ""
    cta: str = ""


class ContentGenerator(Protocol):
    def generate(self, transcript: str, language: str = "vi") -> ContentPackage: ...


class TemplateContentGenerator:
    """Zero-cost deterministic generator; no external LLM is required."""

    def generate(self, transcript: str, language: str = "vi") -> ContentPackage:
        clean = " ".join(transcript.split())
        preview = clean[:500].rstrip()
        hook = "Bạn có biết điều này không?"
        cta = "Theo dõi để xem thêm nội dung hữu ích."
        return ContentPackage(
            title=(clean[:90] or "Video ngắn đáng xem"),
            description=f"{hook}\n\n{preview}\n\n{cta}" if preview else f"{hook}\n\n{cta}",
            hashtags=["#shorts", "#tiktok", "#xuhuong"],
            hook=hook,
            cta=cta,
        )
