from pathlib import PurePath
from typing import Annotated

from fastapi import APIRouter, Form, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import QueueDep, RedisDep, StorageDep
from app.api.errors import ApiError
from app.api.schemas import Instrument, Job, JobCreated, JobOptions, Mode
from app.config import settings
from app.jobs import store
from app.jobs.queue import enqueue

router = APIRouter()

AUDIO_EXTENSIONS = {"wav", "mp3", "m4a", "flac", "ogg", "webm"}
CONTENT_TYPE_EXTENSIONS = {
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/wave": "wav",
    "audio/mpeg": "mp3",
    "audio/mp4": "m4a",
    "audio/x-m4a": "m4a",
    "audio/flac": "flac",
    "audio/ogg": "ogg",
    "audio/webm": "webm",
}
ARTIFACT_MEDIA_TYPES = {
    "score.musicxml": "application/vnd.recordare.musicxml+xml",
    "transcription.mid": "audio/midi",
    "score.pdf": "application/pdf",
}
CHUNK_BYTES = 1024 * 1024


def _extension(file: UploadFile) -> str:
    ext = PurePath(file.filename or "").suffix.lstrip(".").lower()
    if ext in AUDIO_EXTENSIONS:
        return ext
    # MediaRecorder sends e.g. "audio/webm;codecs=opus" with a generic file name.
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type in CONTENT_TYPE_EXTENSIONS:
        return CONTENT_TYPE_EXTENSIONS[content_type]
    raise ApiError(
        400, "UNSUPPORTED_FORMAT", f"Upload one of: {', '.join(sorted(AUDIO_EXTENSIONS))}."
    )


async def _read_limited(file: UploadFile, max_bytes: int) -> bytes:
    data = bytearray()
    while chunk := await file.read(CHUNK_BYTES):
        data += chunk
        if len(data) > max_bytes:
            raise ApiError(
                413, "FILE_TOO_LARGE", f"Files can be at most {settings.max_upload_mb} MB."
            )
    return bytes(data)


@router.post("/jobs", status_code=202)
async def create_job(
    file: UploadFile,
    redis: RedisDep,
    queue: QueueDep,
    storage: StorageDep,
    instrument: Annotated[Instrument, Form()] = "auto",
    mode: Annotated[Mode, Form()] = "solo",
    title: Annotated[str | None, Form(max_length=200)] = None,
) -> JobCreated:
    ext = _extension(file)
    if mode == "full_song":
        raise ApiError(400, "INVALID_REQUEST", "Full-song mode isn't available yet.")
    data = await _read_limited(file, settings.max_upload_mb * 1024 * 1024)

    job_id = store.new_job_id()
    input_key = f"jobs/{job_id}/input.{ext}"
    storage.put(input_key, data)
    options = JobOptions(
        instrument=instrument, mode=mode, title=title or PurePath(file.filename or "").stem or None
    )
    job = store.create(redis, job_id, options)
    enqueue(queue, job_id, input_key)
    return JobCreated(id=job.id, status=job.status)


@router.get("/jobs/{job_id}")
def get_job(job_id: str, redis: RedisDep) -> Job:
    job = store.get(redis, job_id)
    if job is None:
        raise ApiError(404, "NOT_FOUND", "Job not found or expired.")
    return job


@router.get("/jobs/{job_id}/artifacts/{name}")
def get_artifact(job_id: str, name: str, redis: RedisDep, storage: StorageDep) -> FileResponse:
    if name not in ARTIFACT_MEDIA_TYPES:
        raise ApiError(404, "NOT_FOUND", "Unknown artifact.")
    key = f"jobs/{job_id}/{name}"
    if store.get(redis, job_id) is None or not storage.exists(key):
        raise ApiError(404, "NOT_FOUND", "Artifact not found or expired.")
    return FileResponse(storage.get(key), media_type=ARTIFACT_MEDIA_TYPES[name], filename=name)
