# Phase 2: Better piano & notation: steps

Goal: piano scores that read properly (grand staff, real bar lines), plus recording, playback, and PDF export. Exit criteria are in [roadmap.md](../roadmap.md).

Before starting this phase, re-check these steps against what phase 1 actually built.

## 2.1 Piano transcription backend
0. **MAESTRO fixtures (deferred from phase 0).** The v3.0.0 zip is ~100 GB, so don't download it whole: read single members over HTTP range requests (e.g. a one-off `uv run --with remotezip`). Pick 2–3 **test-split** pieces from the metadata CSV (Basic Pitch likely trained on MAESTRO), trim WAV and MIDI to the same ≤ 30 s window, and name them `piano_maestro_<piece>_30s.{wav,mid}`. CC BY-NC-SA 4.0: internal eval only, never shipped.
1. Spike both **ByteDance piano_transcription** and **Transkun** on the MAESTRO fixtures, on CPU inside the container. Pick the one with the better F1 and an acceptable speed (under about 2× the audio's length).
2. Add it as `PianoTranscriber` in `transcribe.py`, behind the same `Transcriber` protocol, with the model loaded once.
3. Choose the backend from the job options: `instrument=piano` → `PianoTranscriber`, otherwise Basic Pitch. Put this choice in one function.
4. The model weights download on first use. Cache them in a Docker volume, and never commit them.
5. Run the eval and record the F1 for each backend in `RESULTS.md`.

## 2.2 Downbeats → bar lines and time signature
1. Spike **Beat This!** in the container to get beat and downbeat times.
2. Replace `estimate_beats` so it returns `(tempo, beat_times, downbeat_times)`. Keep the librosa version as a fallback if Beat This! fails.
3. Time signature = the most common number of beats between downbeats. Limit it to 2/4, 3/4, 4/4, or 6/8, and fall back to 4/4.
4. Start bar 1 at the first downbeat. Notes before it go into a pickup measure.
5. Tests: a 3/4 waltz fixture gives 3/4.

## 2.3 Grand staff
1. When `instrument=piano`, build two parts: treble (pitch ≥ 60) and bass (< 60), grouped as a piano staff group.
2. Fill gaps with rests in each part separately.
3. Tests: a chord that spans middle C splits across the two staves.

Tracking hand position for a smarter split is not part of this phase. Note it in the roadmap if the split at middle C reads badly.

## 2.4 Mic recording
Read first: [styling.md](../styling.md) § Landing (recorder).

1. `src/hooks/useRecorder.ts`: `getUserMedia` → `MediaRecorder` → a webm `Blob`. Show elapsed time and a level from an `AnalyserNode`.
2. Handle these cases: permission denied, no mic, and browsers that don't support webm (Safari records mp4, which the API should accept as `m4a`/`mp4`).
3. Turn the `Blob` into a `File` and pass it to the same `createJob` used for uploads.
4. Stop automatically at `MAX_DURATION_SECONDS`.

## 2.5 MIDI playback with cursor
1. `pnpm add tone @tonejs/midi`.
2. Load `transcription.mid` and schedule it on a Tone `Sampler` loaded with piano samples. Add play, pause, and stop.
3. Cursor: use OSMD's `cursor.show()` and step it with `cursor.next()` on each note-onset time from the **score's** quantized timeline. Don't use the MIDI's times, because they come from a different timeline.
4. Create the AudioContext only after a click, because browsers require a user gesture.

## 2.6 PDF export
1. Add MuseScore 4 to the Dockerfile (AppImage extracted, or the distro package). Headless rendering needs `QT_QPA_PLATFORM=offscreen`.
2. `render.py`: `mscore -o score.pdf score.musicxml` with a timeout. If it fails, log a warning and skip the PDF; the job still succeeds.
3. Add `pdf` to the artifact list only if the file exists. The download menu shows it only when it's there.

## Phase 2 exit check
- MAESTRO piano F1 ≥ 0.85, recorded in `RESULTS.md`.
- A piano fixture opens in MuseScore with correct bar lines, and you don't need to fix anything by hand.
- Record in the browser → score, and play it back with the cursor following along.
