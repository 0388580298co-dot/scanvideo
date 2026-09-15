# ScanVideo

> AI-first short-video localization and publishing platform.

ScanVideo is designed to turn a source short video into a localized Vietnamese short-form package through an observable pipeline:

**Discover → Acquire → Inspect → Transcribe → Translate → Rewrite → Voice → Render → Quality Gate → Schedule → Publish → Analyze**

The project targets creator workflows for legally usable content and platform-approved publishing APIs. It is intentionally designed with provider adapters so one platform or model can be replaced without rewriting the pipeline.

## Core goals

- Discover short-form trends from configurable sources.
- Acquire videos through provider adapters.
- Reject unsuitable inputs early (duration, format, duplicates, quality).
- Transcribe speech with word/segment timestamps.
- Translate and rewrite naturally into Vietnamese.
- Generate synchronized Vietnamese narration and subtitles.
- Preserve useful background audio where possible.
- Render platform-specific variants (9:16, captions, bitrate, duration).
- Score quality before publishing.
- Schedule and publish through official APIs/adapters where supported.
- Track every job, artifact, API attempt and failure for retry/resume.

## Important design principle

ScanVideo does **not** treat downloading and reposting as the same thing as publishing. Source licensing/permission and each platform's terms must be respected. The pipeline includes a source-rights field and a human/automatic quality gate before publishing.

## Architecture

```text
                    ┌──────────────────────────┐
                    │       ScanVideo Web       │
                    │ Dashboard / Jobs / Queue  │
                    └────────────┬─────────────┘
                                 │ REST/WebSocket
                    ┌────────────▼─────────────┐
                    │       FastAPI API         │
                    └────────────┬─────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
      ┌───────▼───────┐  ┌──────▼──────┐  ┌──────▼───────┐
      │ PostgreSQL     │  │ Redis Queue │  │ Object Store │
      │ metadata/jobs  │  │ workers     │  │ media/artifacts│
      └────────────────┘  └──────┬──────┘  └──────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
 ┌──────▼──────┐          ┌───────▼──────┐          ┌──────▼──────┐
 │ Acquisition │          │ AI Pipeline  │          │ Publishing  │
 │ adapters    │          │ ASR/TL/TTS   │          │ adapters    │
 └─────────────┘          │ FFmpeg/QC    │          └─────────────┘
                          └──────────────┘
```

## Planned stack

- Backend: Python 3.12 + FastAPI
- Queue: Redis + Celery initially; abstraction kept open for another worker later
- Database: PostgreSQL + SQLAlchemy/Alembic
- Media: FFmpeg/ffprobe
- ASR: faster-whisper
- Translation: provider abstraction (local/API)
- TTS: provider abstraction (local/API)
- Optional voice/background processing: Demucs + diarization
- Frontend: Next.js + TypeScript
- Deployment: Docker Compose first, then GPU worker deployment
- CI: GitHub Actions

## Pipeline states

`DISCOVERED → DOWNLOADED → VALIDATED → TRANSCRIBED → TRANSLATED → SCRIPTED → TTS_READY → RENDERED → QC_PASSED → SCHEDULED → PUBLISHED`

Any stage can become `FAILED` and resume from the last successful checkpoint.

## Repository layout

```text
scanvideo/
├── apps/
│   ├── api/                 # FastAPI application
│   ├── worker/              # asynchronous media/AI workers
│   └── web/                 # Next.js dashboard (phase 2)
├── packages/
│   └── shared/              # shared schemas/contracts
├── infra/
│   ├── docker/
│   └── migrations/
├── docs/
│   ├── architecture.md
│   └── pipeline.md
├── tests/
├── .env.example
├── docker-compose.yml
└── pyproject.toml
```

## Development status

### Phase 0 — foundation

- [x] Repository initialized
- [x] Architecture documented
- [x] Provider boundaries defined
- [ ] API health endpoint
- [ ] Database models/migrations
- [ ] Redis/Celery worker
- [ ] Acquisition adapter

### Phase 1 — local video pipeline

- [ ] Video validation
- [ ] Audio extraction
- [ ] ASR with timestamps
- [ ] Vietnamese translation/rewrite
- [ ] TTS with duration fitting
- [ ] Subtitle generation
- [ ] FFmpeg rendering
- [ ] Quality gate

### Phase 2 — automation

- [ ] Trend discovery
- [ ] Deduplication/fingerprinting
- [ ] Content scoring
- [ ] Scheduler
- [ ] Official publishing adapters
- [ ] Retry/backoff/idempotency
- [ ] Analytics

### Phase 3 — production

- [ ] GPU worker profile
- [ ] Object storage
- [ ] Secrets management
- [ ] Observability
- [ ] Multi-account support
- [ ] Cost/usage tracking

## Research references

The architecture was informed by open-source projects covering individual parts of the problem: AI video localization/dubbing, Douyin/URL acquisition, timestamped ASR, TTS, FFmpeg rendering, and social scheduling. We intentionally avoid copying project code; ScanVideo uses adapter interfaces and original orchestration.

## License

Project code will be licensed after the dependency/model license matrix is finalized.
