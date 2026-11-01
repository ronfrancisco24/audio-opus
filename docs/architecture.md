# Architecture

## Overview

The app turns an audio recording into sheet music. A user uploads or records audio in the browser. A Python service transcribes it into notes, turns those notes into a notated score, and the browser renders the score and offers downloads.

We use existing open-source models. We do **not** train our own models (see [pipeline.md](pipeline.md)).

```
┌──────────────────────┐   upload audio    ┌────────────────────────┐   enqueue   ┌───────┐
│  web app (Next.js)   │ ────────────────▶ │  transcriber API       │ ──────────▶ │ Redis │
│  - upload / record   │                   │  (FastAPI)             │             └───┬───┘
│  - job status poll   │ ◀──── job JSON ── │  - validate + store    │                 │
│  - score viewer      │                   │  - job status          │         ┌───────▼────────┐
│  - downloads         │ ◀── artifacts ─── │  - serve artifacts     │         │ worker (RQ)    │
└──────────────────────┘                   └───────────┬────────────┘         │ ML pipeline    │
                                                       │                      └───────┬────────┘
                                                       ▼                              │
                                              ┌──────────────────┐   read/write       │
                                              │ Storage           │ ◀─────────────────┘
                                              │ local disk (dev)  │
                                              │ R2 / S3 (prod)    │
                                              └──────────────────┘
```

## Repository layout

```
audio-opus/                    # Repo root = Next.js frontend
├── CLAUDE.md
├── docs/                      # Design docs (this folder)
├── src/app/                   # App Router routes
├── src/components/            # UI components (ui/ = shadcn primitives)
├── src/lib/                   # API client, types, utilities
├── tests/                     # Vitest + Playwright
├── package.json, next.config.ts, tsconfig.json, ...
├── services/
│   └── transcriber/           # Python backend (API + worker)
│       ├── app/
│       │   ├── api/           # FastAPI routes
│       │   ├── pipeline/      # separation, transcription, notation, render
│       │   ├── jobs/          # queue + job state
│       │   ├── storage/       # storage backends (local, s3)
│       │   └── config.py
│       └── tests/
├── fixtures/                  # Small test audio + reference MIDI (git LFS if large)
└── docker-compose.yml         # Redis (+ API/worker) for local dev
```

## Components

### Frontend: repo root
- **Next.js (App Router) + TypeScript (strict) + Tailwind CSS + shadcn/ui.**
- Pages:
  - `/`: landing page with upload and record controls.
  - `/jobs/[id]`: progress while the job runs, then the score viewer and downloads.
- Records from the mic with the `MediaRecorder` API. Uploads with `multipart/form-data` straight to the transcriber API.
- Renders the score with **OpenSheetMusicDisplay (OSMD)** from the MusicXML artifact. OSMD touches `window`, so it is loaded client-side only (`dynamic(..., { ssr: false })`).
- Plays MIDI back in the browser with Tone.js plus `@tonejs/midi` (phase 2).
- No database access and no ML code live in the frontend.

### Transcriber API: `services/transcriber/app/api`
- **Python 3.11 + FastAPI + Pydantic v2.**
- Validates uploads (type, size, duration), saves the original file, creates a job, enqueues it, and returns the job id.
- Serves job status and artifact downloads.
- The contract is in [api.md](api.md).

### Worker: `services/transcriber/app/jobs`
- **RQ (Redis Queue)** worker running the same codebase as the API.
- In dev, the API and worker run in Docker (`docker-compose.yml`), because RQ needs `fork`, which Windows lacks. The image includes ffmpeg and MuseScore.
- Runs the pipeline stages in order and updates the job's `stage` and `progress` in Redis after each one.
- CPU is fine for Basic Pitch. A GPU is needed only for Demucs (phase 3) or heavier models. Those can move to Modal later without changing the API.

### Storage: `services/transcriber/app/storage`
- A `Storage` interface with `put`, `get`, `url`, and `delete`.
- `LocalStorage` (dev): `./data/jobs/{job_id}/...`
- `S3Storage` (prod): Cloudflare R2 through the S3 API.
- Layout of a job's files:
  ```
  jobs/{job_id}/input.<ext>          original upload
  jobs/{job_id}/audio.wav            normalized audio
  jobs/{job_id}/transcription.mid    raw transcription
  jobs/{job_id}/score.musicxml       quantized notation
  jobs/{job_id}/score.pdf            rendered PDF (optional)
  ```
- Job files expire after 7 days in the MVP.

## Request flow

1. The browser sends `POST /jobs` with the audio file and options.
2. The API validates the file, stores `input.<ext>`, creates the job (`status=queued`), enqueues it, and returns `{ id }`.
3. The browser goes to `/jobs/{id}` and polls `GET /jobs/{id}` every 1.5 s.
4. The worker runs: normalize → (separate) → transcribe → notate → render. It updates the stage and progress as it goes.
5. When the job is `done`, the browser fetches `score.musicxml` and renders it with OSMD. Download buttons link to the MIDI, MusicXML, and PDF artifacts.

## Key decisions

| Decision | Choice | Why |
|---|---|---|
| Models | Use pretrained open-source models | Training needs large datasets and GPUs; existing models are good enough |
| ML language | Python | Basic Pitch, music21, Demucs, and librosa are all Python |
| Queue | RQ + Redis | Simpler than Celery; enough for this workload |
| Score format | MusicXML | Standard format; OSMD, MuseScore, and Verovio all read it |
| Renderer | OSMD | Renders MusicXML directly in the browser; mature |
| Upload path | Browser → FastAPI directly | Avoids Vercel's ~4.5 MB request body limit on route handlers |
| Status updates | Polling | Simple; switch to SSE only if polling becomes a problem |
| Auth | None in MVP | Added in phase 4 (Supabase) |

## Environment variables

**Web (`.env.local` at the repo root)**
- `NEXT_PUBLIC_API_URL`: base URL of the transcriber API (e.g. `http://localhost:8000`)

**Transcriber (`services/transcriber/.env`)**
- `REDIS_URL`: e.g. `redis://localhost:6379/0`
- `STORAGE_BACKEND`: `local` or `s3`
- `STORAGE_LOCAL_DIR`: e.g. `./data`
- `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`: prod only
- `CORS_ORIGINS`: comma-separated, e.g. `http://localhost:3000`
- `MAX_UPLOAD_MB` (default `50`), `MAX_DURATION_SECONDS` (default `600`)

## Deployment (target)
- **Web:** Vercel.
- **API + worker:** Railway or Fly.io. Start on CPU; move the GPU stages to Modal when Demucs arrives.
- **Redis:** Upstash or a managed Redis from the host.
- **Storage:** Cloudflare R2.
