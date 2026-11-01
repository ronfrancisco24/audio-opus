# Phase 3: Full songs & deploy: steps

Goal: a mixed song gives usable melody and bass lines, and the app runs in production. Exit criteria are in [roadmap.md](../roadmap.md).

These steps are an outline. Make them detailed when phase 2 is done.

## 3.1 Source separation (Demucs)
1. Spike `htdemucs` and `htdemucs_6s` on 2–3 songs. Time each on CPU and on a GPU.
2. `separate.py`: `separate(wav) -> dict[stem, Path]`, with the model loaded once. Save stems as `jobs/{id}/stems/{name}.wav`.
3. Run it only when `mode=full_song`. Add its progress weight to the job runner.
4. Enable the "Full song" option in the UI.

## 3.2 Stem selection / multi-part score
1. Add an option to the API: `stems: ["vocals", "bass", ...]` (default: melody + bass). Update api.md, schemas.py, and types.ts together.
2. Transcribe each chosen stem with the right backend: `piano` → piano model, others → Basic Pitch with the frequency range clamped.
3. Combine the stems into one music21 `Score`, one part per stem, sharing the same beat grid.

## 3.3 GPU stages on Modal
1. Wrap `separate` (and the heavy transcribers, if needed) as Modal functions.
2. The worker calls Modal for those stages and runs everything else locally. Choose with an env var, e.g. `GPU_BACKEND=local|modal`.
3. Pass audio by storage key (R2), not by sending the bytes.

## 3.4 S3/R2 storage and deploy
1. `S3Storage` uses `boto3` with `S3_ENDPOINT_URL`. The artifact endpoint returns `302` to a presigned URL.
2. Add an R2 lifecycle rule that deletes `jobs/` after 7 days.
3. Deploy: the web app on Vercel, the API and worker on Railway/Fly from the same Dockerfile, Redis on Upstash.
4. Set `CORS_ORIGINS` to the Vercel domain. Health checks use `/health`.
5. If uploads become slow or large, switch to presigned direct-to-R2 uploads, and update api.md to match.

## Phase 3 exit check
- A pop song in `full_song` mode gives a usable melody and bass part.
- The full flow works on the deployed URLs.
