# CLAUDE.md

An app that turns audio recordings into sheet music. A Next.js frontend uploads audio to a Python (FastAPI) service. An RQ worker transcribes the audio with pretrained models (Basic Pitch first), quantizes the notes into a score with music21, and returns MusicXML/MIDI/PDF. The browser renders the MusicXML with OpenSheetMusicDisplay.

**Current phase:** Phase 0 (docs and scaffolding). See `docs/roadmap.md`. Some commands below don't work until scaffolding is done.

## Docs: read the relevant one before changing that area
- `docs/architecture.md`: components, repo layout, request flow, env vars, key decisions
- `docs/pipeline.md`: ML/music pipeline stages, `NoteEvent`, notation rules, evaluation
- `docs/api.md`: HTTP contract between web and transcriber
- `docs/styling.md`: design tokens, typography, layout, screens, accessibility
- `docs/testing.md`: test strategy, fixtures, what to run before calling something done
- `docs/roadmap.md`: phases and exit criteria
- `docs/steps/phase-*.md`: ordered build steps for each feature in each phase. Follow them in order, and tick them off in the roadmap

If a change makes a doc wrong, update the doc in the same change.

## Layout
```
./ (repo root)            Next.js (App Router, TS strict, Tailwind v4): src/, package.json, ...
services/transcriber/     Python 3.11, FastAPI + RQ worker, uv
  app/api/                routes + Pydantic schemas
  app/pipeline/           normalize, separate, transcribe, notate, render
  app/jobs/               queue + job state
  app/storage/            local / S3 backends
fixtures/                 short test audio + reference MIDI
docs/                     design docs
```

## Commands
Web (repo root, pnpm):
- `pnpm dev`: dev server at http://localhost:3000
- `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm test:e2e`

Transcriber (`services/transcriber`, uv):
- `docker compose up`: Redis + API (http://localhost:8000) + worker
- `uv run ruff check . && uv run ruff format .`
- `uv run pytest` (fast, native) · `docker compose run --rm worker uv run pytest -m model` (loads models) · `... -m eval` (accuracy)

The dev machine is Windows. RQ workers need `fork`, which native Windows doesn't have, so the API and worker run in Linux containers. The image includes ffmpeg and, from phase 2, MuseScore. Only the web app and fast Python tests run natively.

## Rules
- **Don't train or fine-tune models.** Use pretrained ones behind the `Transcriber` interface (`app/pipeline/transcribe.py`). Add a new model as a new backend, not by changing the callers.
- **All ML and music logic is Python.** The frontend never does transcription or notation.
- **Build notation from `NoteEvent`s, not by re-importing the MIDI file.** Transcription MIDI uses a fake tempo.
- **Load models once per worker process**, never per job or per request.
- **Keep the API contract in sync:** `services/transcriber/app/api/schemas.py` ↔ `src/lib/api/types.ts` ↔ `docs/api.md`.
- **Styling uses design tokens only** (`bg-surface`, `text-muted`, …). No raw hex values or Tailwind palette colors in components. The score paper stays white in dark mode.
- OSMD and other code that touches the browser are loaded client-only (`dynamic(..., { ssr: false })`).
- Never commit audio outside `fixtures/`, model weights, `data/`, or `.env*` files.
- Stay inside the current phase's scope. If something belongs to a later phase, note it in `docs/roadmap.md` instead of building it.

## Code style
- **TypeScript:** strict, no `any`. Server Components by default; add `"use client"` only where needed. Components are PascalCase files in `src/components/`, and hooks are named `useX` in `src/hooks/`.
- **Python:** type hints everywhere, Pydantic v2 for I/O, `ruff` for lint and format (line length 100). Pipeline stages are plain functions with clear inputs and outputs; no global state except the cached model.
- Errors that reach the user use the error codes in `docs/api.md`.

## Definition of done
Lint, typecheck, and tests pass in every package touched (see `docs/testing.md`). Pipeline changes also need an eval run with the F1 score compared against `tests/eval/RESULTS.md`.
