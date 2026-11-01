from datetime import UTC, datetime
from typing import Any

from redis import Redis
from ulid import ULID

from app.api.schemas import Job, JobOptions

TTL_SECONDS = 7 * 24 * 3600


def _key(job_id: str) -> str:
    return f"job:{job_id}"


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def new_job_id() -> str:
    return f"j_{ULID()}"


def create(redis: Redis, job_id: str, options: JobOptions) -> Job:
    now = _now()
    job = Job(id=job_id, status="queued", created_at=now, updated_at=now, options=options)
    redis.set(_key(job_id), job.model_dump_json(), ex=TTL_SECONDS)
    return job


def get(redis: Redis, job_id: str) -> Job | None:
    raw = redis.get(_key(job_id))
    return Job.model_validate_json(raw) if raw else None


def update(redis: Redis, job_id: str, **fields: Any) -> Job:
    job = get(redis, job_id)
    if job is None:
        raise KeyError(job_id)
    # Re-validate so a bad stage/progress fails here, not in a client.
    job = Job.model_validate({**job.model_dump(), **fields, "updated_at": _now()})
    redis.set(_key(job_id), job.model_dump_json(), keepttl=True)
    return job
