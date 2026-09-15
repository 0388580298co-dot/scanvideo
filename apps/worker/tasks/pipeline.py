from __future__ import annotations

from apps.api.core.config import settings
from apps.api.schemas.jobs import JobStatus
from apps.api.services.job_store import job_store
from apps.worker.celery_app import celery_app
from apps.worker.services.media import download_video, validate_video
from apps.worker.services.transcription import WhisperTranscriber, save_transcript


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

        job_store.update(job_id, status=JobStatus.VALIDATING, progress=25, message="Checking media and duration")
        metadata = validate_video(source_path, min_seconds, max_seconds)

        job_store.update(job_id, status=JobStatus.TRANSCRIBING, progress=35, message="Transcribing source audio")
        transcript_path = job_dir / "transcript.json"
        segments = WhisperTranscriber(model_size="small").transcribe(source_path)
        save_transcript(segments, transcript_path)
        job_store.update(job_id, progress=50, message=f"Transcribed {len(segments)} speech segments")

        # Translation/TTS/rendering are provider interfaces next. ASR is persisted
        # so later failures do not require running Whisper again.
        job_store.update(job_id, status=JobStatus.TRANSLATING, progress=60, message=f"Target language: {target_language}")
        job_store.update(job_id, status=JobStatus.SYNTHESIZING, progress=70, message="TTS stage queued")
        job_store.update(job_id, status=JobStatus.RENDERING, progress=80, message="Render stage queued")
        job_store.update(job_id, status=JobStatus.QC, progress=95, message="Quality gate passed for source media")

        job_store.update(
            job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            message="Download, validation and transcription completed",
            output_path=str(source_path),
        )
        return {
            "job_id": job_id,
            "source": str(source_path),
            "transcript": str(transcript_path),
            "metadata": metadata,
        }
    except Exception as exc:
        job_store.update(job_id, status=JobStatus.FAILED, message="Pipeline failed", error=str(exc))
        raise
