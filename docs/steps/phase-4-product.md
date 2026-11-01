# Phase 4: Product: steps

Goal: accounts, history, editing, sharing, and limits. These steps are an outline. Make them detailed when phase 3 is done.

## 4.1 Auth & job history
1. Supabase Auth on the web side (`@supabase/ssr`).
2. The API verifies the Supabase JWT from `Authorization: Bearer`. Jobs get a `user_id`.
3. Store jobs in Postgres (Supabase) instead of only in Redis. Redis remains the queue.
4. A `/history` page lists the user's jobs.
5. Update api.md: auth header, `GET /jobs` (list).

## 4.2 Basic score editing
1. Choose the editing approach after a spike: OSMD isn't an editor. Try selecting a note in the rendered SVG and editing the MusicXML, or an editor library.
2. Start small: change one note's pitch and duration, then save a new `score.musicxml` version.
3. Re-export MIDI and PDF from the edited MusicXML on the server, using music21 and MuseScore.

## 4.3 Shareable links
1. A `share_token` on the job. `GET /share/{token}` gives a read-only view.
2. The owner can turn sharing on and off.

## 4.4 Usage limits
1. Limit jobs per user per day, plus a total audio duration cap. Enforce it in `POST /jobs` with a new `429` error code, documented in api.md.
2. Rate-limit anonymous use by IP, or require login to transcribe.
