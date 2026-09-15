from __future__ import annotations

from apps.api.core.config import settings
from apps.api.schemas.jobs import JobStatus
from apps.api.services.job_store import job_store
from apps.worker.celery_app import celery_app
from apps.worker.services.audio import build_tts_manifest, extract_audio
from apps.worker.services.audio_mix import mix_narration_with_background
from apps.worker.services.media import download_video, validate_video
from apps.worker.services.qc import quality_gate
from apps.worker.services.render import render_subtitles
from apps.worker.services.subtitles import write_srt
from apps.worker.services.transcription import WhisperTranscriber, save_transcript
from apps.worker.services.translation import translate_segments
from apps.worker.services.tts import EdgeTTSProvider, synthesize_segments
from apps.worker.services.vertical import render_vertical


def _artifact_ready(path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


@celery_app.task(
    bind=True,
    name="scanvideo.run_pipeline",
    autoretry_for=(TimeoutError, ConnectionError),
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
    max_retries=2,
)
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

        audio_path = job_dir / "source.wav"
        transcript_path = job_dir / "transcript.json"
        if not _artifact_ready(transcript_path):
            job_store.update(job_id, status=JobStatus.TRANSCRIBING, progress=30, message="Transcribing source audio")
            if not _artifact_ready(audio_path):
                extract_audio(source_path, audio_path)
            segments = WhisperTranscriber(model_size=settings.whisper_model).transcribe(audio_path)
            if not segments:
                raise RuntimeError("No speech segments were detected")
            save_transcript(segments, transcript_path)
        else:
            import json
            from apps.worker.services.transcription import TranscriptSegment
            segments = [TranscriptSegment(**item) for item in json.loads(transcript_path.read_text(encoding="utf-8"))]

        translation_path = job_dir / f"translation.{target_language}.json"
        subtitle_path = job_dir / f"subtitles.{target_language}.srt"
        if _artifact_ready(translation_path):
            import json
            from apps.worker.services.translation import TranslationSegment
            translated = [TranslationSegment(**item) for item in json.loads(translation_path.read_text(encoding="utf-8"))["segments"]]
        else:
            job_store.update(job_id, status=JobStatus.TRANSLATING, progress=55, message=f"Translating to {target_language}")
            translated = translate_segments(segments, target_language, translation_path)
        if not _artifact_ready(subtitle_path):
            write_srt(translated, subtitle_path)
        manifest_path = job_dir / "tts_manifest.json"
        if not _artifact_ready(manifest_path):
            build_tts_manifest(translated, manifest_path)

        tts_dir = job_dir / "tts"
        narration_paths = synthesize_segments(EdgeTTSProvider(voice=settings.tts_voice, rate=settings.tts_rate), translated, tts_dir)

        narrated_path = job_dir / "localized_narration.mp4"
        if not _artifact_ready(narrated_path):
            job_store.update(job_id, status=JobStatus.RENDERING, progress=75, message="Mixing narration with original audio")
            mix_narration_with_background(source_path, narration_paths, translated, narrated_path, narration_gain_db=settings.narration_gain_db, background_gain_db=settings.background_gain_db)

        final_path = job_dir / "final_vi.mp4"
        if not _artifact_ready(final_path):
            render_subtitles(narrated_path, subtitle_path, final_path)

        vertical_path = job_dir / "final_vi_9x16.mp4"
        if not _artifact_ready(vertical_path):
            render_vertical(final_path, vertical_path, settings.output_width, settings.output_height)

        job_store.update(job_id, status=JobStatus.QC, progress=95, message="Running final quality checks")
        qc = quality_gate(vertical_path, expected_min_duration=min_seconds, expected_width=settings.output_width, expected_height=settings.output_height)
        if not qc["passed"]:
            raise RuntimeError(f"Quality gate failed: {qc}")

        job_store.update(job_id, status=JobStatus.COMPLETED, progress=100, message="Localized vertical video rendered and QC passed", output_path=str(vertical_path))
        return {"job_id": job_id, "output": str(vertical_path), "metadata": metadata, "qc": qc, "auto_publish": auto_publish}
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
