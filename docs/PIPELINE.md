# ScanVideo pipeline

## Current flow

`download -> validate -> transcribe -> translate -> TTS -> audio mix -> subtitles -> QC -> completed`

The worker now creates a real localized output instead of marking a job complete after only preparing assets.

## Media rules

- Source playlists are disabled.
- Minimum/maximum duration are validated before expensive processing.
- TTS is generated per transcript segment and time-fitted without pitch shifting.
- Original audio is retained as a quieter background layer.
- Vietnamese narration is mixed at the source timeline.
- Subtitles are burned into the final MP4.
- Final output must contain playable video and audio and pass FFmpeg decode validation.
- `apps/worker/services/vertical.py` provides a 1080x1920 vertical master for short-form platforms.
- `apps/worker/services/dedup.py` provides SHA-256 source fingerprints for duplicate prevention.

## Important provider boundary

`apps/worker/services/translation.py` currently exposes a provider boundary and passthrough implementation. A production deployment must configure a real translation provider before publishing localized content.

TTS currently uses Edge TTS through the provider boundary and can run without a paid API key. Only use voices and source media you are authorized to use.

## Publishing

Publishing adapters should use official platform APIs and OAuth. Do not bypass CAPTCHAs, access controls, rate limits, or platform security mechanisms.
