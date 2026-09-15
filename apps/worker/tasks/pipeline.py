from __future__ import annotations

import json

from apps.api.core.config import settings
from apps.api.schemas.jobs import JobStatus
from apps.api.services.job_store import job_store
from apps.worker.celery_app import celery_app
from apps.worker.services.audio import build_tts_manifest, extract_audio
from apps.worker.services.audio_mix import mix_narration_with_background
from apps.worker.services.content import TemplateContentGenerator
from apps.worker.services.media import download_video, sha256_file, validate_video
from apps.worker.services.qc import quality_gate
from apps.worker.services.render import render_subtitles
from apps.worker.services.subtitles import write_srt
from apps.worker.services.transcription import TranscriptSegment, WhisperTranscriber, save_transcript
from apps.worker.services.translation import TranslationSegment, translate_segments
from apps.worker.services.tts import EdgeTTSProvider, synthesize_segments
from apps.worker.services.vertical import render_vertical


def _artifact_ready(path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def _load_transcript(path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return None, [TranscriptSegment(**item) for item in payload]
    return payload.get("language"), [TranscriptSegment(**item) for item in payload.get("segments", [])]


def _load_or_create_content(job_id: str, translated: list[TranslationSegment], path) -> dict:
    if _artifact_ready(path):
        return json.loads(path.read_text(encoding="utf-8"))
    text = " ".join(segment.translated_text.strip() for segment in translated if segment.translated_text.strip())
    package = TemplateContentGenerator().generate(text, language="vi")
    payload = {"title": package.title, "description": package.description, "hashtags": package.hashtags, "hook": package.hook, "cta": package.cta}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    job_store.update(job_id, content_package=payload)
    return payload


@celery_app.task(bind=True, name="scanvideo.run_pipeline", autoretry_for=(TimeoutError, ConnectionError), retry_backoff=True, retry_backoff_max=120, retry_jitter=True, max_retries=2)
def run_pipeline(self, job_id: str, source_url: str, target_language: str, min_duration: float | None = None, max_duration: float | None = None, auto_publish: bool = False) -> dict:
    job_dir = settings.media_root / "jobs" / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    min_seconds = min_duration if min_duration is not None else settings.min_video_duration
    max_seconds = max_duration if max_duration is not None else settings.max_video_duration
    try:
        source_path = next((p for p in job_dir.glob("source.*") if p.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}), None)
        if source_path is None:
            job_store.update(job_id, status=JobStatus.DOWNLOADING, progress=10, message="Downloading source video")
            source_path = download_video(source_url, job_dir)
        job_store.update(job_id, status=JobStatus.VALIDATING, progress=20, message="Checking media and duration")
        metadata = validate_video(source_path, min_seconds, max_seconds)
        fingerprint = sha256_file(source_path)
        existing = job_store.find_source_by_fingerprint(fingerprint)
        if existing is not None and existing.job_id != job_id:
            raise RuntimeError(f"Duplicate source media detected; already processed by job {existing.job_id}")
        if existing is None:
            try:
                job_store.register_source_media(job_id=job_id, source_url=source_url, fingerprint=fingerprint, path=str(source_path), duration=metadata["duration"], width=metadata["width"], height=metadata["height"])
            except Exception as exc:
                existing = job_store.find_source_by_fingerprint(fingerprint)
                if existing is not None and existing.job_id != job_id:
                    raise RuntimeError(f"Duplicate source media detected; already processed by job {existing.job_id}") from exc
                raise

        audio_path = job_dir / "source.wav"
        transcript_path = job_dir / "transcript.json"
        if not _artifact_ready(transcript_path):
            job_store.update(job_id, status=JobStatus.TRANSCRIBING, progress=30, message="Transcribing source audio")
            if not _artifact_ready(audio_path):
                extract_audio(source_path, audio_path)
            transcriber = WhisperTranscriber(
                model_size=settings.whisper_model,
                device=settings.whisper_device,
                compute_type=settings.whisper_compute_type,
            )
            segments = transcriber.transcribe(audio_path)
            if not segments:
                raise RuntimeError("No speech segments were detected")
            source_language = transcriber.detected_language or "en"
            save_transcript(segments, transcript_path, source_language)
        else:
            source_language, segments = _load_transcript(transcript_path)
            source_language = source_language or "en"
            if not segments:
                raise RuntimeError("Cached transcript contains no valid segments")

        translation_path = job_dir / f"translation.{target_language}.json"
        subtitle_path = job_dir / f"subtitles.{target_language}.srt"
        if _artifact_ready(translation_path):
            payload = json.loads(translation_path.read_text(encoding="utf-8"))
            translated = [TranslationSegment(**item) for item in payload["segments"]]
        else:
            job_store.update(job_id, status=JobStatus.TRANSLATING, progress=55, message=f"Translating {source_language} to {target_language}")
            translated = translate_segments(segments, target_language, translation_path, source_language=source_language)
        if not _artifact_ready(subtitle_path):
            write_srt(translated, subtitle_path)

        content_path = job_dir / "content.json"
        job_store.update(job_id, status=JobStatus.SCRIPTED, progress=60, message="Generating title, description and hashtags")
        content = _load_or_create_content(job_id, translated, content_path)

        manifest_path = job_dir / "tts_manifest.json"
        if not _artifact_ready(manifest_path):
            build_tts_manifest(translated, manifest_path)
        job_store.update(job_id, status=JobStatus.SYNTHESIZING, progress=65, message="Generating Vietnamese narration")
        tts_dir = job_dir / "tts"
        narration_paths = synthesize_segments(EdgeTTSProvider(voice=settings.tts_voice, rate=settings.tts_rate), translated, tts_dir)

        narrated_path = job_dir / "localized_narration.mp4"
        if not _artifact_ready(narrated_path):
            job_store.update(job_id, status=JobStatus.RENDERING, progress=75, message="Mixing narration with original audio")
            mix_narration_with_background(source_path, narration_paths, translated, narrated_path, narration_gain_db=settings.narration_gain_db, background_gain_db=settings.background_gain_db)
        final_path = job_dir / "final_vi.mp4"
        if not _artifact_ready(final_path):
            job_store.update(job_id, status=JobStatus.RENDERING, progress=82, message="Burning Vietnamese subtitles")
            render_subtitles(narrated_path, subtitle_path, final_path)
        vertical_path = job_dir / "final_vi_9x16.mp4"
        if not _artifact_ready(vertical_path):
            job_store.update(job_id, status=JobStatus.RENDERING, progress=90, message="Rendering 9:16 vertical output")
            render_vertical(final_path, vertical_path, settings.output_width, settings.output_height)
        job_store.update(job_id, status=JobStatus.QC, progress=95, message="Running final quality checks")
        qc = quality_gate(vertical_path, expected_min_duration=min_seconds, expected_width=settings.output_width, expected_height=settings.output_height)
        if not qc["passed"]:
            raise RuntimeError(f"Quality gate failed: {qc}")
        job_store.update(job_id, status=JobStatus.COMPLETED, progress=100, message="Localized vertical video rendered and QC passed", output_path=str(vertical_path), content_package=content)
        return {"job_id": job_id, "output": str(vertical_path), "metadata": metadata, "qc": qc, "auto_publish": auto_publish, "content": content}
    except (TimeoutError, ConnectionError) as exc:
        retries = getattr(self.request, "retries", 0)
        if retries >= self.max_retries:
            job_store.update(job_id, status=JobStatus.FAILED, message="Pipeline failed after retries", error=str(exc))
        else:
            job_store.update(job_id, message=f"Temporary error; retry {retries + 1}/{self.max_retries}", error=str(exc))
        raise
    except Exception as exc:
        job_store.update(job_id, status=JobStatus.FAILED, message="Pipeline failed", error=str(exc))
        raise
