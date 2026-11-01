# Phase 1: MVP: steps

Goal: a solo recording goes in, and a single-staff score you can view and download comes out. Exit criteria are in [roadmap.md](../roadmap.md).

Build in this order. Each feature can be tested before the next one starts.

## 1.1 Storage (local backend)
Read first: [architecture.md](../architecture.md) § Storage.

1. In `app/storage/__init__.py`, define the `Storage` protocol: `put(key, bytes|Path)`, `get(key) -> Path`, `exists(key)`, `delete_prefix(prefix)`.
2. `LocalStorage(root)` writes under `STORAGE_LOCAL_DIR`. Keys look like `jobs/{id}/score.musicxml`.
3. Reject keys containing `..` or starting with `/`, because keys come partly from user input.
4. Write tests for a put/get round trip and for rejecting traversal keys.

Expiring files after 7 days waits until deploy (phase 3). Locally, delete `data/` whenever you like.

## 1.2 Job model and queue
Read first: [api.md](../api.md) (status, stage, progress, error codes).

1. In `app/api/schemas.py`, write Pydantic models that match api.md exactly: `JobOptions`, `JobResult`, `JobError`, `Job`.
2. In `app/jobs/store.py`, store the job as JSON in Redis under `job:{id}`, with a 7-day TTL. Add `create`, `get`, and `update(stage=, progress=, ...)`.
3. In `app/jobs/queue.py`, enqueue `run_job(job_id, input_key)` on RQ by import path, so the API never imports the ML stack. The job timeout is 10 minutes.
4. For tests, use `fakeredis` (`uv add --dev fakeredis`), and run RQ with `is_async=False` so jobs run inline.

## 1.3 API endpoints
1. `POST /jobs` checks, in this order:
   - extension or content type in the allowed list → else `400`
   - size ≤ `MAX_UPLOAD_MB` (read in chunks; stop once over the limit) → else `413`
   - then it stores `input.<ext>`, creates the job, enqueues it, and returns `202 {id, status}`.
2. `GET /jobs/{id}` returns the job, or `404` in the shared error shape.
3. `GET /jobs/{id}/artifacts/{name}` checks `name` against an allow-list of the three file names, then returns a `FileResponse` with the content type from api.md.
4. Add an exception handler so every error comes back as `{ "error": { code, message } }`.
5. Write API tests: a happy path using a fixture file, wrong type, too large, unknown job, and an artifact name like `../x`.

Checking the audio's duration happens in the worker (normalize stage), which then fails the job with `AUDIO_TOO_LONG`.

## 1.4 Pipeline: normalize
Read first: [pipeline.md](../pipeline.md) § Stage 1.

1. `normalize(input_path) -> wav_path` runs `ffmpeg -i in -ac 1 -ar 22050 -af silenceremove...,loudnorm`, called with `subprocess.run([...], check=True)`. Pass arguments as a list, never through a shell.
2. Read the duration with `soundfile.info`. If it's over `MAX_DURATION_SECONDS`, raise `PipelineError("AUDIO_TOO_LONG")`.
3. If ffmpeg fails, raise `PipelineError("UNREADABLE_AUDIO")`.
4. Mark the tests `model`-free; they need ffmpeg, so run them in the container. Test that a fixture gives a 22,050 Hz mono file, and that a text file renamed to `.mp3` raises `UNREADABLE_AUDIO`.

## 1.5 Pipeline: transcribe (Basic Pitch)
Read first: [pipeline.md](../pipeline.md) § Stage 3.

1. **Spike first:** in the container, run `uv add basic-pitch` and transcribe one fixture by hand. If TensorFlow causes trouble, use the ONNX backend instead.
2. `app/pipeline/types.py`: the `NoteEvent` dataclass.
3. `app/pipeline/transcribe.py`: the `Transcriber` protocol plus `BasicPitchTranscriber`. Load the model once at module level and cache it with `functools.cache`.
4. Convert Basic Pitch's `note_events` to `NoteEvent`s, and write `transcription.mid` from its `midi_data`.
5. If no notes come out, raise `NO_NOTES_DETECTED`.
6. Add a `@pytest.mark.model` test: the C major scale fixture gives the 8 expected pitches in order.

## 1.6 Pipeline: notate
Read first: [pipeline.md](../pipeline.md) § Stage 4, steps 1–5, 7, and 8. Grand staff and downbeats come in phase 2.

1. `uv add librosa music21`.
2. `estimate_beats(wav) -> (tempo_bpm, beat_times)` using `librosa.beat.beat_track`.
3. `to_beats(t, beat_times) -> float`: interpolate between beats with `numpy.interp`, and extrapolate at the ends using the mean beat length.
4. `build_score(notes, tempo, title) -> music21.stream.Score`: one part in 4/4, notes grouped into chords by quantized onset, `quantize((4, 3))`, key from `analyze('key')`, clef chosen from the median pitch.
5. Write `score.musicxml`. Return `tempo`, `key`, `time_signature`, and `note_count` for `JobResult`.
6. Tests use hand-built `NoteEvent` lists, so they need no model:
   - 4 quarter notes at 120 bpm → 4 quarter notes in one bar
   - two notes with the same onset → one chord
   - slightly early or late onsets snap to the grid
   - low notes → bass clef

## 1.7 Worker job runner
1. `app/jobs/run.py` defines `run_job(job_id, input_key)`, which runs normalize → transcribe → notate in order. Update `stage` and `progress` using the weights in pipeline.md (no separate stage yet).
2. `PipelineError(code)` → job `failed` with that code. Any other exception → `INTERNAL` with a generic message. Log the traceback, but never show it to the user.
3. On success: `status=done`, plus the `result` and its artifact URLs (no `pdf` yet).
4. Write a `model` test that runs one fixture end to end through `run_job`.

## 1.8 Web: API client and types
Read first: [api.md](../api.md).

1. `src/lib/api/types.ts`: TypeScript types that mirror `schemas.py`.
2. `src/lib/api/client.ts` with `createJob(file, options)`, `getJob(id)`, and `artifactUrl(path)`, built on `fetch` and `NEXT_PUBLIC_API_URL`. Non-2xx responses throw an error that carries `code`.
3. Vitest tests with a mocked `fetch`: a successful parse, and an error response that throws with its code.

## 1.9 Web: landing page with upload
Read first: [styling.md](../styling.md) § Landing. **Wait for the design before final styling.** Build the behavior with plain markup first.

1. `src/components/UploadDropzone.tsx` (client): a real `<input type="file" accept=...>` wrapped in a drop zone, which keeps it accessible for free. Check type and size on the client too, to give faster feedback; the server still validates.
2. An instrument `<select>`. Mode stays solo-only for now.
3. On submit: `createJob` → `router.push(/jobs/{id})`. Disable the button while uploading.
4. Show API errors inline.

## 1.10 Web: job page and progress
1. `src/app/jobs/[id]/page.tsx`. In Next 16, `params` is a Promise, so `await` it. Render a client component, `JobView`.
2. `src/hooks/useJob.ts`: poll `getJob` every 1.5 s while the job is `queued` or `running`, and stop on `done`, `failed`, or unmount.
3. `JobProgress`: the stage list plus a `<progress>` bar, inside an `aria-live="polite"` region.
4. Write a Vitest test for `useJob`: it stops polling on `done`. Use fake timers.

## 1.11 Web: score viewer and downloads
1. `pnpm add opensheetmusicdisplay`.
2. `src/components/ScoreViewer.tsx` (client): load OSMD with a dynamic import inside `useEffect`, then `osmd.load(musicxmlUrl)` and `render()`. Re-render when the container resizes.
3. Wrap the score in a white "paper" container. It stays white in dark mode.
4. Downloads are plain `<a href={artifactUrl} download>` links for MusicXML and MIDI.
5. Show the meta row: key · tempo · time signature · duration.

## 1.12 Error states
1. Map each error code in api.md to a plain-language message and a hint, e.g. `NO_NOTES_DETECTED` → "We couldn't hear any notes. Try a clearer recording of a single instrument."
2. `ErrorState` component with a "Try again" link back to `/`.
3. A job that isn't found or has expired (404) gets its own message.
4. Write a unit test checking that every code from `types.ts` has a message. That way, a new code can't ship without one.

## Phase 1 exit check
- An end-to-end run: upload a 30-second solo fixture, see the score, and download both files, all in under 60 seconds.
- `uv run pytest -m eval` → F1 ≥ 0.7. Record the result in `services/transcriber/tests/eval/RESULTS.md`.
- Playwright: one e2e test (upload → done → the score SVG is present), run against a mocked API.
