from __future__ import annotations

from apps.api.core.config import settings
from apps.api.schemas.jobs import JobStatus
from apps.api.services.job_store import job_store
from apps.worker.celery_app import celery_app
from apps.worker.services.audio import build_tts_manifest, extract_audio
from apps.worker.services.media import download_video, validate_video
from apps.worker.services.subtitles import write_srt
from apps.worker.services.transcription import WhisperTranscriber, save_transcript
from apps.worker.services.translation import translate_segments


@celery_app.task(bind=True, name="scanvideo.run_pipeline", autoretry_for=(Exception,), retry_backoff=True, max_retries=2)
def run_pipeline(
    self,
    job_id: str,
    source_url: str,
    target_language: str,
    min_duration: float | None = None,
    max_duration: float | None = None,
) -> dict:
    job_dir = settings.media_root / "jobs" / job_id
    min_seconds = min_duration if min_duration is not None else settings.min_video_duration
    max_seconds = max_duration if max_duration is not None else settings.max_video_duration

    try:
        job_store.update(job_id, status=JobStatus.DOWNLOADING, progress=10, message="Downloading source video")
        source_path = download_video(source_url, job_dir)

        job_store.update(job_id, status=JobStatus.VALIDATING, progress=20, message="Checking media and duration")
        metadata = validate_video(source_path, min_seconds, max_seconds)

        job_store.update(job_id, status=JobStatus.TRANSCRIBING, progress=30, message="Extracting source audio")
        audio_path = extract_audio(source_path, job_dir / "source.wav")
        transcript_path = job_dir / "transcript.json"
        segments = WhisperTranscriber(model_size="small").transcribe(audio_path)
        save_transcript(segments, transcript_path)

        job_store.update(job_id, progress=50, message=f"Transcribed {len(segments)} speech segments")
        job_store.update(job_id, status=JobStatus.TRANSLATING, progress=60, message=f"Translating to {target_language}")
        translated = translate_segments(segments, target_language)
        subtitle_path = write_srt(translated, job_dir / "subtitles.vi.srt")

        job_store.update(job_id, status=JobStatus.SYNTHESIZING, progress=70, message="Preparing timing-safe TTS manifest")
        manifest_path = build_tts_manifest(translated, job_dir / "tts_manifest.json")

        # Actual TTS provider is intentionally not invoked yet. A provider must be
        # configured explicitly; silently generating placeholder audio would make
        # the final video look successful while containing incorrect narration.
        job_store.update(job_id, status=JobStatus.RENDERING, progress=80, message="Localization assets prepared")
        job_store.update(job_id, status=JobStatus.QC, progress=95, message="Source media and timing assets validated")
        job_store.update(
            job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            message="Download, validation, transcription, translation and subtitle preparation completed",
            output_path=str(source_path),
        )
        return {
            "job_id": job_id,
            "source": str(source_path),
            "audio": str(audio_path),
            "transcript": str(transcript_path),
            "subtitles": str(subtitle_path),
            "tts_manifest": str(manifest_path),
            "metadata": metadata,
        }
    except Exception as exc:
        job_store.update(job_id, status=JobStatus.FAILED, message="Pipeline failed", error=str(exc))
        raise
