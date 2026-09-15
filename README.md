# ScanVideo

> AI-first short-video localization and publishing platform.

ScanVideo turns legally usable source media into a Vietnamese short-form package through an observable, resumable pipeline:

**Discover → Acquire → Validate → Transcribe → Translate → Rewrite → Voice → Render → QC → Schedule → Publish → Analyze**

## Current status

The repository is currently in **Phase 1 / core pipeline hardening**. The API, Celery/Redis foundation, media validation, timestamp-preserving local translation adapter, Edge TTS, subtitle/rendering services, vertical output, QC, and development job store exist. PostgreSQL persistence, dashboard UI, full scheduler, and production publishing flows remain subsequent phases.

## $0 AI API design

The default pipeline does not require OpenAI, Gemini, Claude, or ElevenLabs API keys.

- ASR: `faster-whisper`
- Translation: `Argos Translate` (local model required)
- TTS: `edge-tts`
- Metadata: deterministic `TemplateContentGenerator`
- Media: FFmpeg/ffprobe

Optional commercial providers must remain optional and are never imported by the default local translation path.

## Architecture

```text
Dashboard / client
       ↓ REST
     FastAPI
       ↓
 Redis + Celery ───── PostgreSQL (Phase 2)
       ↓
 Download → Validate → Whisper → Argos → TTS → Mix → SRT → 9:16 → QC
       ↓
 Official YouTube / TikTok publisher adapters
```

Provider boundaries are kept in `apps/worker/services` so ASR, translation, TTS, download, and publishing implementations can be replaced without rewriting orchestration.

## Repository layout

```text
scanvideo/
├── apps/api/                 # FastAPI API, schemas, development job store
├── apps/worker/              # Celery tasks and media/AI providers
├── docs/                     # Architecture, pipeline, local AI and security notes
├── infra/docker/             # Docker image
├── tests/                    # Fast unit tests
├── .env.example
├── docker-compose.yml
└── pyproject.toml
```

## Requirements

- Windows 10/11 or Linux
- Python 3.12+ for local development
- Docker Desktop for the recommended Windows setup
- FFmpeg/ffprobe when running outside Docker
- An English→Vietnamese Argos model for local translation

## Docker quick start

```powershell
copy .env.example .env
docker compose up -d --build
docker compose ps
```

API: `http://localhost:8000`
Swagger: `http://localhost:8000/docs`
Health: `http://localhost:8000/health`

## Local development

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev,media,translation]"
pytest -q
ruff check .
```

## Configuration

See `.env.example`. Important defaults:

```env
MIN_VIDEO_DURATION=10
MAX_VIDEO_DURATION=180
WHISPER_MODEL=small
TRANSLATION_PROVIDER=argos
TTS_PROVIDER=edge
TTS_VOICE=vi-VN-HoaiMyNeural
OUTPUT_WIDTH=1080
OUTPUT_HEIGHT=1920
```

A source below 10 seconds is rejected; 10.0 seconds is accepted. Artifacts are stored per job under `/data/media/jobs/{job_id}/` and the pipeline reuses valid checkpoints where possible.

## API

Implemented now:

- `GET /health`
- `GET /api/v1`
- `POST /api/v1/jobs`
- `GET /api/v1/jobs`
- `GET /api/v1/jobs/{job_id}`
- `GET /api/v1/jobs/{job_id}/status`
- `GET /api/v1/dashboard/summary`
- `GET /api/v1/dashboard/jobs`

Publishing, scheduling, trends, and analytics endpoints are being added only when their backing implementation is real.

## Quality and safety

QC requires a non-empty file, video stream, audio stream, expected 1080×1920 dimensions, valid duration, and a full FFmpeg decode check. The project does not bypass DRM/CAPTCHA/anti-bot controls, steal cookies or sessions, access private content without authorization, or bypass platform rate limits.

Only download, transform, and publish content you are legally permitted to use.

See `docs/LOCAL_AI.md` and `docs/SECURITY.md` for details.
