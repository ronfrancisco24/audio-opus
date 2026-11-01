# Audio Opus
This was a project I had in mind for a while now, I just didn't make the time for it until now. 
This is basically an audio to sheet music transcriber and I hope it works haha! (Will update the README once it's complete)

## What it does
Upload or record a short clip of someone playing an instrument, and Audio Opus writes it out as sheet music. You can read the score in the browser and download it as MusicXML (opens in MuseScore, Finale, Sibelius, etc.) or MIDI.

## How it works
1. **Upload:** the web app sends the audio to a Python API, which queues a job.
2. **Clean up:** a background worker converts the audio to a standard format with ffmpeg.
3. **Transcribe:** a pretrained model ([Basic Pitch](https://github.com/spotify/basic-pitch)) detects which notes are played and when.
4. **Notate:** [librosa](https://librosa.org/) estimates the tempo, then [music21](https://web.mit.edu/music21/) works out the key and snaps the notes to a rhythmic grid to make a readable score.
5. **Display:** the browser renders the score with [OpenSheetMusicDisplay](https://opensheetmusicdisplay.org/).

No models are trained here; it builds on existing open-source ones.

## Tech stack
- **Web:** Next.js, TypeScript, Tailwind CSS, shadcn/ui
- **Backend:** Python, FastAPI, Redis + RQ for background jobs, Docker
- **Music/ML:** Basic Pitch, librosa, music21, ffmpeg

## Status
Work in progress. The plan:
- **Phase 1:** single instrument → single-staff score *(in progress)*
- **Phase 2:** better piano transcription (two-hand grand staff), mic recording, playback, PDF export
- **Phase 3:** full songs: separate the instruments first, then transcribe the melody or bass line; go live online
- **Phase 4:** accounts, job history, simple score editing, and shareable links

See [`docs/roadmap.md`](docs/roadmap.md) for details.
