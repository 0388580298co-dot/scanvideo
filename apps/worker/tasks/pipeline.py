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

        job_store.update(job_id, status=JobStatus.TRANSCRIBING, progress=30, message="Extracting and transcribing source audio")
        audio_path = extract_audio(source_path, job_dir / "source.wav")
        transcript_path = job_dir / "transcript.json"
        segments = WhisperTranscriber(model_size="small").transcribe(audio_path)
        if not segments:
            raise RuntimeError("No speech segments were detected")
        save_transcript(segments, transcript_path)

        job_store.update(job_id, progress=50, message=f"Transcribed {len(segments)} speech segments")
        job_store.update(job_id, status=JobStatus.TRANSLATING, progress=55, message=f"Translating to {target_language}")
        translated = translate_segments(segments, target_language)
        subtitle_path = write_srt(translated, job_dir / f"subtitles.{target_language}.srt")
        build_tts_manifest(translated, job_dir / "tts_manifest.json")

        job_store.update(job_id, status=JobStatus.SYNTHESIZING, progress=65, message="Generating timing-safe narration")
        tts_dir = job_dir / "tts"
        voice = getattr(settings, "tts_voice", "vi-VN-HoaiMyNeural")
        rate = getattr(settings, "tts_rate", "+0%")
        provider = EdgeTTSProvider(voice=voice, rate=rate)
        narration_paths = synthesize_segments(provider, translated, tts_dir)

        job_store.update(job_id, status=JobStatus.RENDERING, progress=80, message="Mixing narration and rendering subtitles")
        narrated_path = job_dir / "localized_narration.mp4"
        mix_narration_with_background(
            source_path,
            narration_paths,
            translated,
            narrated_path,
            narration_gain_db=3.0,
            background_gain_db=-10.0,
        )
        final_path = job_dir / "final_vi.mp4"
        render_subtitles(narrated_path, subtitle_path, final_path)

        vertical_path = job_dir / "final_vi_9x16.mp4"
        render_vertical(final_path, vertical_path)

        job_store.update(job_id, status=JobStatus.QC, progress=95, message="Running final quality checks")
        qc = quality_gate(vertical_path, expected_min_duration=max(1.0, min_seconds))
        if not qc.get("passed"):
            raise RuntimeError(f"Quality gate failed: {qc}")

        job_store.update(
            job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            message="Localized vertical video rendered and QC passed",
            output_path=str(vertical_path),
        )
        return {
            "job_id": job_id,
            "source": str(source_path),
            "audio": str(audio_path),
            "transcript": str(transcript_path),
            "subtitles": str(subtitle_path),
            "tts_manifest": str(job_dir / "tts_manifest.json"),
            "narrated_video": str(narrated_path),
            "output": str(final_path),
            "vertical_output": str(vertical_path),
            "metadata": metadata,
            "qc": qc,
        }
    except Exception as exc:
        job_store.update(job_id, status=JobStatus.FAILED, message="Pipeline failed", error=str(exc))
        raise
