# ScanVideo release checklist

## Automated locally

- Download source with yt-dlp
- Reject videos outside configured duration limits
- Transcribe with faster-whisper
- Translate with OpenAI when `OPENAI_API_KEY` is available
- Generate Vietnamese TTS with Edge TTS
- Fit narration to transcript timing
- Mix narration with original background audio
- Burn subtitles
- Run final media QC
- Produce final MP4 and optional 9:16 master

## Requires your intervention

### OpenAI
Set `OPENAI_API_KEY` for real AI translation. The Responses API supports structured JSON output; the project uses a JSON translation response contract.

### YouTube
A Google OAuth flow and `youtube.upload` authorization are required before the service can publish to your channel. Keep tokens out of Git.

### TikTok
Create a TikTok developer app, enable Content Posting API, obtain the required approved scope and user authorization, then provide the resulting access token. TikTok currently documents Direct Post and Upload workflows and restricts unaudited clients to private viewing.

### Rights
Only process and publish media for which you have the necessary rights/permission. Platform eligibility and monetization are not guaranteed by automation.
