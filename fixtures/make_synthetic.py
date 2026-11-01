"""Generate synthetic fixture clips (.wav) with exact reference MIDI (.mid).

Stdlib only. Run from the repo root: `python fixtures/make_synthetic.py`.
Synthetic tones are for pipeline smoke tests; use real recordings for accuracy eval.
"""

import math
import struct
import wave
from pathlib import Path

SR = 22050
TICKS_PER_SECOND = 960  # 480 ticks per quarter at 120 bpm
OUT = Path(__file__).parent

# (pitch, start_s, duration_s)
Note = tuple[int, float, float]


def scale() -> list[Note]:
    return [(p, i * 1.0, 0.9) for i, p in enumerate([60, 62, 64, 65, 67, 69, 71, 72])]


def melody() -> list[Note]:
    # "Twinkle Twinkle" first phrase (public domain), quarter = 0.5 s
    pitches = [60, 60, 67, 67, 69, 69, 67, 65, 65, 64, 64, 62, 62, 60]
    beats = [1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 2]
    notes, t = [], 0.0
    for p, b in zip(pitches, beats, strict=True):
        notes.append((p, t, b * 0.5 - 0.05))
        t += b * 0.5
    return notes


def chords() -> list[Note]:
    triads = [[48, 60, 64, 67], [53, 60, 65, 69], [55, 59, 62, 67], [48, 60, 64, 67]]
    return [(p, i * 2.0, 1.9) for i, chord in enumerate(triads) for p in chord]


def render_wav(notes: list[Note], seconds: float, path: Path) -> None:
    buf = [0.0] * int(seconds * SR)
    for pitch, start, dur in notes:
        freq = 440.0 * 2 ** ((pitch - 69) / 12)
        s0 = int(start * SR)
        for i in range(int(dur * SR)):
            t = i / SR
            env = min(1.0, t / 0.005) * math.exp(-3.0 * t)  # short attack, piano-like decay
            tone = sum(math.sin(2 * math.pi * freq * h * t) / h**1.5 for h in (1, 2, 3, 4))
            buf[s0 + i] += env * tone
    peak = max(abs(x) for x in buf) or 1.0
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(x / peak * 0.8 * 32767)) for x in buf))


def var_len(n: int) -> bytes:
    out = [n & 0x7F]
    while n := n >> 7:
        out.append((n & 0x7F) | 0x80)
    return bytes(reversed(out))


def write_midi(notes: list[Note], path: Path) -> None:
    events = []  # (tick, order, bytes); note-offs sort before note-ons at the same tick
    for pitch, start, dur in notes:
        events.append((round(start * TICKS_PER_SECOND), 1, bytes([0x90, pitch, 80])))
        events.append((round((start + dur) * TICKS_PER_SECOND), 0, bytes([0x80, pitch, 0])))
    track = var_len(0) + b"\xff\x51\x03" + (500_000).to_bytes(3, "big")  # 120 bpm
    last = 0
    for tick, _, data in sorted(events):
        track += var_len(tick - last) + data
        last = tick
    track += var_len(0) + b"\xff\x2f\x00"
    header = b"MThd" + struct.pack(">IHHH", 6, 0, 1, 480)
    path.write_bytes(header + b"MTrk" + struct.pack(">I", len(track)) + track)


if __name__ == "__main__":
    for name, notes in [("c_major_scale", scale()), ("twinkle", melody()), ("chords", chords())]:
        stem = OUT / f"synth_{name}_8s"
        render_wav(notes, 8.0, stem.with_suffix(".wav"))
        write_midi(notes, stem.with_suffix(".mid"))
        print(stem.name)
