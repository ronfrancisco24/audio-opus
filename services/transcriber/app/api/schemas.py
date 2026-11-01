"""API models. Mirror of docs/api.md and src/lib/api/types.ts; change all three together."""

from datetime import datetime
from typing import (
    Literal,
    NotRequired,  # pydantic needs these on Python < 3.12
)

from pydantic import BaseModel, Field
from typing_extensions import TypedDict

Instrument = Literal["auto", "piano", "guitar", "voice", "other"]
Mode = Literal["solo", "full_song"]
Status = Literal["queued", "running", "done", "failed"]
Stage = Literal["normalizing", "separating", "transcribing", "notating", "rendering"]
JobErrorCode = Literal[
    "UNREADABLE_AUDIO",
    "AUDIO_TOO_LONG",
    "NO_NOTES_DETECTED",
    "TRANSCRIPTION_FAILED",
    "NOTATION_FAILED",
    "INTERNAL",
]


class JobOptions(BaseModel):
    instrument: Instrument = "auto"
    mode: Mode = "solo"
    title: str | None = None


class Artifacts(TypedDict):
    musicxml: str
    midi: str
    pdf: NotRequired[str]  # left out when PDF rendering isn't available


class JobResult(BaseModel):
    duration_s: float
    tempo_bpm: float
    key: str
    time_signature: str
    note_count: int
    artifacts: Artifacts


class JobError(BaseModel):
    code: JobErrorCode
    message: str


class Job(BaseModel):
    id: str
    status: Status
    stage: Stage | None = None
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime
    updated_at: datetime
    options: JobOptions
    result: JobResult | None = None
    error: JobError | None = None


class JobCreated(BaseModel):
    id: str
    status: Status
