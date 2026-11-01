# ML / Music Pipeline

All of this runs in the worker (`services/transcriber/app/pipeline/`). Each stage is a pure-ish function: it takes inputs, returns outputs, and writes its artifacts to storage. That keeps each stage testable on its own.

```
input.<ext> ─▶ normalize ─▶ [separate] ─▶ transcribe ─▶ notate ─▶ render
                audio.wav     stems/*.wav   NoteEvent[]   score.musicxml  score.pdf
                                            transcription.mid
```

## Shared types

```python
@dataclass(frozen=True)
class NoteEvent:
    start_s: float      # onset time in seconds
    end_s: float        # offset time in seconds
    pitch: int          # MIDI note number 0–127
    velocity: int       # 1–127
    confidence: float   # model amplitude/confidence, 0–1
```

The **notation stage builds the score from `NoteEvent`s, not by re-importing the MIDI file**. MIDI files from transcription have a fake fixed tempo, so re-importing them loses the real timing.

## Stage 1: Normalize (`normalize.py`)
- Use **ffmpeg** (system dependency) to decode any supported input to **mono WAV at 22,050 Hz**, which is Basic Pitch's native rate.
- Reject files over `MAX_DURATION_SECONDS`.
- Trim leading and trailing silence, and normalize loudness to about −1 dBFS peak.
- Accepted inputs: `wav, mp3, m4a, flac, ogg, webm` (`webm` is what the browser's MediaRecorder produces).

## Stage 2: Separate (`separate.py`) — phase 3
- **Demucs** (`htdemucs`) splits audio into `vocals, drums, bass, other` (`htdemucs_6s` adds `piano` and `guitar`).
- Runs only when the user picks "full song" mode. Solo recordings skip it.
- Needs a GPU for reasonable speed, so it's the first stage to move to Modal.

## Stage 3: Transcribe (`transcribe.py`)
Transcription backends sit behind one interface:

```python
class Transcriber(Protocol):
    name: str
    def transcribe(self, wav_path: Path) -> list[NoteEvent]: ...
```

| Backend | Use | Phase | Notes |
|---|---|---|---|
| **Basic Pitch** (Spotify) | Default, any single instrument | 1 | Apache 2.0, CPU-friendly, polyphonic |
| **ByteDance piano_transcription** or **Transkun** | `instrument=piano` | 2 | Much better piano accuracy, including pedal |
| **MT3** (Google) | Multi-instrument | Later / maybe | Heavy; needs a GPU |

Basic Pitch notes:
- Start with its default thresholds. Expose `onset_threshold`, `frame_threshold`, and `minimum_note_length` in config only, not in the UI, until testing shows they need tuning.
- Clamp `minimum_frequency` and `maximum_frequency` to the selected instrument's range when one is known, to cut ghost notes.
- Also write `transcription.mid` for download.
- Load the model **once per worker process**, not once per job.

## Stage 4: Notate (`notate.py`) — the hard part
This turns the timed notes into readable notation. Most of the quality work happens here.

1. **Tempo and beats**
   - Phase 1: `librosa.beat.beat_track` gives a single global tempo plus beat times.
   - Phase 2: **Beat This!** (or madmom) for downbeats, which give the bar lines and time signature.
   - Default to 4/4 when downbeat detection isn't available.
2. **Convert times to beats.** Map each `start_s` and `end_s` onto the beat grid. Interpolate between detected beat times so tempo drift is handled, rather than using one fixed BPM.
3. **Quantize** onsets and durations to the nearest 1/16 note, or to triplet 1/8 notes when that fits better. In music21: `quarterLengthDivisors=(4, 3)`.
4. **Clean up**
   - Drop notes shorter than a 1/32 note after quantization.
   - Merge repeated identical notes that overlap.
   - Fill gaps with rests.
5. **Key signature:** `music21` `stream.analyze('key')`. It affects how notes are spelled (e.g. F♯ vs G♭).
6. **Staves**
   - Phase 1: one staff, with a treble or bass clef picked from the median pitch.
   - Phase 2, piano: grand staff, split at middle C (MIDI 60). Phase 2+ adds a smarter split that tracks hand position.
7. **Voices/chords:** notes with the same quantized onset become chords.
8. Write **`score.musicxml`** with music21 and set title, tempo marking, and key/time signatures.

## Stage 5: Render (`render.py`)
- The browser renders MusicXML with OSMD. That's the main view, and no server-side rendering is needed for it.
- PDF export uses the **MuseScore 4 CLI** (`mscore -o score.pdf score.musicxml`) when MuseScore is installed on the worker. If it isn't, skip the PDF and leave it out of the artifacts list.

## Progress reporting
The stage weights below drive `progress` (0–1) in the job status:

| Stage | Weight |
|---|---|
| normalize | 0.05 |
| separate | 0.35 (only when enabled; others are rescaled) |
| transcribe | 0.40 |
| notate | 0.15 |
| render | 0.05 |

## Evaluation
- Use **`mir_eval.transcription`** for note-level precision, recall, and F1 (onset tolerance 50 ms) against reference MIDI.
- Reference data: hand-made fixtures in `fixtures/`, plus a few short **MAESTRO** piano clips from phase 2.
- Track the F1 score per backend in `services/transcriber/tests/eval/`. Run it with `pytest -m eval`; it's slow, so it's not part of the default run.
- Judge notation quality by hand: open the result in MuseScore and check that it's readable.

## Known limits (MVP)
- Best on clean, solo, single-instrument recordings.
- Expect mistakes on vocals, heavy reverb, distortion, and full mixes until phase 3.
- No dynamics, articulations, or pedal markings in the notation yet.
