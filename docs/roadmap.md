# Roadmap

We build in phases. Finish a phase and check it against its exit criteria before starting the next one.

## Phase 0: Docs & scaffolding
- [x] Design docs (`docs/`)
- [x] `CLAUDE.md`
- [x] `git init`, `.gitignore` (Node, Python, `data/`, `.env*`, model weights)
- [x] Scaffold the Next.js app at the repo root: Next.js 16 + TS strict + Tailwind v4, ESLint, Prettier, Vitest
- [x] Design color tokens in `src/app/globals.css` (see `docs/styling.md`)
- [x] Add shadcn/ui (Button) and a dark-mode toggle
- [x] Scaffold `services/transcriber`: uv project, FastAPI, RQ, ruff, pytest
- [x] `docker-compose.yml` with Redis, API, and worker
- [x] Synthetic test clips + reference MIDI in `fixtures/` (`make_synthetic.py`)
- [ ] Real recordings in `fixtures/` (needed before phase 1 eval). MAESTRO clips moved to phase 2

**Exit:** `pnpm dev` serves a placeholder page; `GET /health` returns ok; Redis is running.

## Phase 1: MVP (solo instrument → single-staff score) ← current
- [x] `POST /jobs`, `GET /jobs/{id}`, artifact download (see [api.md](api.md))
- [x] Local storage backend
- [ ] Pipeline: normalize (ffmpeg) → Basic Pitch → notate (librosa tempo, music21 quantize, key) → MusicXML
- [ ] Landing page with upload; job page with progress
- [ ] OSMD score viewer; MusicXML and MIDI downloads
- [ ] Error states for every error code

**Exit:** A clean 30-second solo piano or melody clip produces a readable single-staff score in under 60 seconds on CPU. Note F1 is at least 0.7 on the fixture set.

## Phase 2: Better piano & notation
- [ ] MAESTRO test-split clips + MIDI in `fixtures/`, trimmed to ≤ 30 s (deferred from phase 0)
- [ ] Piano backend (ByteDance piano_transcription or Transkun) chosen when `instrument=piano`
- [ ] Beat This! downbeats → bar lines and time signature
- [ ] Grand staff with the hand split at middle C
- [ ] Mic recording in the browser (MediaRecorder → webm)
- [ ] MIDI playback (Tone.js) with a cursor following along in OSMD
- [ ] PDF export through the MuseScore CLI

**Exit:** Piano F1 is at least 0.85 on the MAESTRO clips, and the grand staff is readable in MuseScore without manual fixes to bar lines.

## Phase 3: Full songs
- [ ] Demucs source separation (`mode=full_song`)
- [ ] Pick which stem to transcribe (or several, giving a multi-part score)
- [ ] Move GPU stages to Modal
- [ ] S3/R2 storage backend; deploy (Vercel + Railway/Fly + Upstash)

**Exit:** A pop song gives a usable melody line and a usable bass line.

## Phase 4: Product
- [ ] Supabase auth; job history per user
- [ ] Basic score editing (fix a note's pitch or duration, then re-export)
- [ ] Shareable links
- [ ] Usage limits

## Not planned (for now)
- Training custom models
- Tabs for guitar (possible later from the same note data)
- Live transcription in real time
