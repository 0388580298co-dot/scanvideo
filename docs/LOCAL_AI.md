# Local AI

ScanVideo's default localization path does not require OpenAI, Gemini, Claude, ElevenLabs, or another paid AI API.

## Default providers

- ASR: `faster-whisper` (CPU or CUDA)
- Translation: `Argos Translate` with a locally installed language model
- TTS: `edge-tts` using the configured Vietnamese voice
- Content metadata: deterministic `TemplateContentGenerator`
- Media: FFmpeg/ffprobe

## Argos model setup

The Python package alone is not enough: an English-to-Vietnamese Argos language package must be installed in the same environment as the worker. The application intentionally fails with a clear `TranslationError` when the configured local model is missing; it never silently falls back to untranslated source text.

## Performance

Set `WHISPER_MODEL=small` for the default balance. Smaller models reduce CPU/RAM use; larger models improve transcription quality at higher resource cost. If CUDA is available, faster-whisper can use it automatically.

## Cost

The core AI pipeline can run without a paid AI API. `edge-tts` is a network TTS service rather than an application-owned local model, so availability and service terms should be checked before production use.
