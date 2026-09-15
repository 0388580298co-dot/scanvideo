# ScanVideo

> AI-first, local-first short-video localization and publishing platform.

ScanVideo turns legally usable source media into a Vietnamese short-form package through an observable, resumable pipeline:

**Discover → Acquire → Validate → Transcribe → Translate → Rewrite → Voice → Mix → Subtitle → 9:16 → QC → Schedule → Publish → Analyze**

## Current implementation

The repository now contains the core pipeline, PostgreSQL-backed jobs and source deduplication, deterministic content generation, resumable TTS/render artifacts, Celery + Redis workers, Celery Beat scheduling, a Next.js dashboard, platform account management, official YouTube/TikTok OAuth adapters, durable scheduled publishing, analytics endpoints, Docker Compose, migrations, tests, and CI.

Real publishing still requires the user's own platform application credentials and permissions. No API secret or token is committed to this repository.

## $0 AI API design

The default localization path does not require OpenAI, Gemini, Claude, or ElevenLabs API keys.

- ASR: `faster-whisper`
- Translation: `Argos Translate` with a locally installed language model
- TTS: `edge-tts`
- Metadata: deterministic `TemplateContentGenerator`
- Media: FFmpeg/ffprobe

Optional commercial providers remain optional. The default pipeline does not require them.

## Architecture

```text
Next.js Dashboard / API client
             ↓ REST
          FastAPI
             ↓
      PostgreSQL ←→ SQLAlchemy/Alembic
             ↓
       Redis ←→ Celery Worker
             ↑       ↓
          Celery Beat
             ↓
Download → Validate → Whisper → Argos → Script → TTS
    → Audio Mix → SRT → 9:16 → QC
             ↓
       ScheduledPost
             ↓
Official YouTube / TikTok APIs
             ↓
      PublishedPost → Analytics
```

Provider boundaries live under `apps/worker/services` and publishing adapters are isolated from pipeline orchestration.

## Repository layout

```text
scanvideo/
├── apps/api/                 # FastAPI, schemas, DB and OAuth routes
├── apps/worker/              # Celery tasks and media/AI/publishing providers
├── web/                      # Next.js dashboard
├── docs/                     # Architecture, pipeline, local AI and security
├── infra/docker/             # Docker images
├── infra/migrations/         # Alembic migrations
├── tests/                    # Unit tests
├── .env.example
├── docker-compose.yml
├── alembic.ini
└── pyproject.toml
```

## Requirements

- Windows 10/11 or Linux
- Python 3.12+
- Docker Desktop on Windows (recommended)
- FFmpeg/ffprobe outside Docker
- Argos source→Vietnamese language model for local translation

## Docker quick start

```powershell
copy .env.example .env
docker compose up -d --build
docker compose ps
```

Services:

```text
api      → http://localhost:8000
web      → http://localhost:3000
postgres → 5432
redis    → 6379
worker
beat
```

Swagger: `http://localhost:8000/docs`  
Health: `http://localhost:8000/health`

## Local development

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev,media,translation,publishing]"
pytest -q
ruff check .
```

## Job pipeline

Every job has an isolated directory:

```text
media/jobs/{job_id}/
├── source.*
├── source.wav
├── transcript.json
├── translation.vi.json
├── content.json
├── subtitles.vi.srt
├── tts_manifest.json
├── tts/
├── localized_narration.mp4
├── final_vi.mp4
├── final_vi_9x16.mp4
└── qc.json
```

Valid artifacts are reused so a failed job can resume instead of starting from zero.

The mandatory source-duration policy is:

```text
< 10.0s  → reject
10.0s    → accept
> 180s   → reject by default
```

## API

### Jobs

```text
POST /api/v1/jobs
GET  /api/v1/jobs
GET  /api/v1/jobs/{job_id}
GET  /api/v1/jobs/{job_id}/status
```

### Scheduling

```text
POST /api/v1/schedule
GET  /api/v1/schedule
```

Schedules are persisted in PostgreSQL. Celery Beat checks due posts every 30 seconds and dispatches them to the publishing worker.

### Platform accounts

```text
POST /api/v1/accounts
GET  /api/v1/accounts
POST /api/v1/accounts/{account_id}/disable
```

### OAuth

```text
GET /api/v1/oauth/youtube/start
GET /api/v1/oauth/youtube/callback
GET /api/v1/oauth/tiktok/start
GET /api/v1/oauth/tiktok/callback
```

OAuth uses official platform flows. Tokens are stored outside the repository in the configured secret root.

### Analytics

```text
GET /api/v1/analytics/summary
GET /api/v1/analytics/published
```

## YouTube

The project uses the official YouTube Data API and OAuth 2.0. The upload adapter uses resumable media upload and defaults to private visibility. Real publishing requires a Google Cloud OAuth client and the YouTube Data API enabled.

## TikTok

The project uses TikTok Login Kit OAuth and Content Posting API. Direct posting requires the appropriate approved scope. TikTok's current Direct Post API requires querying creator information and honoring the privacy options returned by TikTok. Unaudited clients are restricted to private visibility by TikTok.

## Security

Never commit:

```text
.env
.secrets/
client_secret*.json
*.pem
*.key
*_token.json
```

No password, cookie, session or platform credential is required by the application source. OAuth state is validated to reduce CSRF risk. Publishing only uses official APIs.

The system does not bypass DRM, CAPTCHA, anti-bot controls, rate limits, private-content controls, or authentication.

## Testing and CI

Python CI runs Ruff and Pytest. Dashboard CI runs TypeScript type checking and Next.js production build.

If GitHub Actions is still running, its result should be treated as authoritative for the exact repository revision; local media integration tests require FFmpeg and AI model dependencies.

## Windows notes

Docker Desktop is the recommended Windows path because it supplies PostgreSQL, Redis, FFmpeg and the Python worker environment consistently. For native execution, use PowerShell and install FFmpeg/ffprobe on PATH.

## Copyright / content rights

Only download, transform, and publish content that you own or are legally permitted to use. Platform APIs and AI providers have their own terms, quotas, audits and content policies.
