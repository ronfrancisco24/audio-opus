# Transcriber API

Base URL is set by `NEXT_PUBLIC_API_URL` (dev: `http://localhost:8000`). All responses are JSON unless noted. Field names are `snake_case`.

The frontend's TypeScript types in `src/lib/api/types.ts` must mirror the Pydantic models in `services/transcriber/app/api/schemas.py`. Change both together.

## `POST /jobs`
Creates a transcription job.

**Request:** `multipart/form-data`

| Field | Type | Required | Notes |
|---|---|---|---|
| `file` | file | yes | `wav, mp3, m4a, flac, ogg, webm`; ≤ `MAX_UPLOAD_MB` |
| `instrument` | string | no | `auto` (default), `piano`, `guitar`, `voice`, `other` |
| `mode` | string | no | `solo` (default) or `full_song` (phase 3; enables source separation) |
| `title` | string | no | Score title; defaults to the file name |

**Response `202`**
```json
{ "id": "j_01JB6Z...", "status": "queued" }
```

**Errors:** `400 UNSUPPORTED_FORMAT` (neither the extension nor the content type is allowed) · `400 INVALID_REQUEST` (missing file, bad `instrument`/`mode`, `title` over 200 chars, or `mode=full_song` before phase 3) · `413 FILE_TOO_LARGE`.
Audio that is too long or unreadable is accepted here and fails the job later (`AUDIO_TOO_LONG`, `UNREADABLE_AUDIO`), because duration is checked in the worker.

## `GET /jobs/{id}`
Returns the job's status. The frontend polls this.

**Response `200`**
```json
{
  "id": "j_01JB6Z...",
  "status": "running",
  "stage": "transcribing",
  "progress": 0.42,
  "created_at": "2026-10-20T14:03:11Z",
  "updated_at": "2026-10-20T14:03:29Z",
  "options": { "instrument": "piano", "mode": "solo", "title": "Nocturne" },
  "result": null,
  "error": null
}
```

- `status`: `queued | running | done | failed`
- `stage`: `normalizing | separating | transcribing | notating | rendering | null`
- `progress`: `0.0`–`1.0`

When `status` is `done`:
```json
"result": {
  "duration_s": 94.2,
  "tempo_bpm": 88,
  "key": "E- major",
  "time_signature": "4/4",
  "note_count": 812,
  "artifacts": {
    "musicxml": "/jobs/j_01JB6Z.../artifacts/score.musicxml",
    "midi": "/jobs/j_01JB6Z.../artifacts/transcription.mid",
    "pdf": "/jobs/j_01JB6Z.../artifacts/score.pdf"
  }
}
```
`pdf` is left out when PDF rendering isn't available.

When `status` is `failed`:
```json
"error": { "code": "TRANSCRIPTION_FAILED", "message": "Human-readable explanation" }
```

Error codes: `UNREADABLE_AUDIO`, `AUDIO_TOO_LONG`, `NO_NOTES_DETECTED`, `TRANSCRIPTION_FAILED`, `NOTATION_FAILED`, `INTERNAL`.

**Errors:** `404 NOT_FOUND`: job not found or expired.

## `GET /jobs/{id}/artifacts/{name}`
Downloads an artifact. `name` is one of `score.musicxml`, `transcription.mid`, or `score.pdf`.
- In dev the file is streamed directly. In prod this may return `302` to a signed R2 URL.
- Content types: `application/vnd.recordare.musicxml+xml`, `audio/midi`, `application/pdf`.
- **Errors:** `404 NOT_FOUND` for an unknown job, a name outside the list, or an artifact that doesn't exist (yet).

## `GET /health`
Returns `{ "status": "ok" }`. Used for deploy health checks.

## Conventions
- Job ids are prefixed ULIDs (`j_...`), so they sort by time and are hard to guess.
- CORS allows only origins listed in `CORS_ORIGINS`.
- Every error response uses this shape: `{ "error": { "code": "...", "message": "..." } }`.
- HTTP error codes: `UNSUPPORTED_FORMAT`, `INVALID_REQUEST`, `FILE_TOO_LARGE`, `NOT_FOUND`, `INTERNAL`. Job error codes are listed under `GET /jobs/{id}`.
- No auth in the MVP. Phase 4 adds a Supabase JWT in the `Authorization: Bearer` header.
