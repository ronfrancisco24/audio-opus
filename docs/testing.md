# Testing

## Frontend (repo root)
- **Vitest + React Testing Library** for components and `src/lib` logic (API client, formatting).
- **Playwright** for end-to-end tests: upload a fixture → wait for `done` → the score renders → downloads work. In CI, run it against a mocked API (MSW). Locally it can run against the real stack.
- Mock OSMD in unit tests. It needs a real DOM and canvas.

## Backend (`services/transcriber`)
- **pytest**
  - Unit tests for each pipeline stage. Notation tests use hand-built `NoteEvent` lists, so they need no model.
  - API tests with FastAPI's `TestClient` and a fake queue that runs jobs inline.
  - Mark tests that load real models with `@pytest.mark.model`. Mark the accuracy suite with `@pytest.mark.eval`. Neither runs by default.
- **Accuracy eval:** `mir_eval.transcription` F1 against reference MIDI in `fixtures/`. Record the results in `tests/eval/RESULTS.md` when a backend or parameters change.

## Fixtures (`fixtures/`)
- Keep clips short (5–30 s) and small. Each one has a matching reference `.mid` where possible.
- Name them `<instrument>_<description>_<seconds>s.<ext>`, e.g. `piano_c_major_scale_8s.wav`.
- `synth_*` clips come from `fixtures/make_synthetic.py` (stdlib only) and have exact reference MIDI. Use them for smoke tests; real recordings for accuracy.
- Use only audio we have the rights to (our own recordings, or MAESTRO under CC BY-NC-SA 4.0 for internal eval).

## Before calling a change done
- `pnpm lint && pnpm typecheck && pnpm test` at the repo root
- `uv run ruff check . && uv run ruff format --check . && uv run pytest` in `services/transcriber`
- For pipeline changes, run `uv run pytest -m eval` and compare the F1 score with the last recorded result.
