import fakeredis
import pytest
from pydantic import ValidationError
from rq import Queue

from app.api.schemas import JobOptions
from app.jobs import store
from app.jobs.queue import JOB_TIMEOUT_SECONDS, enqueue


def test_create_and_get(redis: fakeredis.FakeRedis) -> None:
    job_id = store.new_job_id()
    created = store.create(redis, job_id, JobOptions(title="Scale"))
    assert job_id.startswith("j_")
    assert store.get(redis, job_id) == created
    assert created.status == "queued" and created.stage is None and created.progress == 0.0
    assert 0 < redis.ttl(f"job:{job_id}") <= store.TTL_SECONDS


def test_get_missing(redis: fakeredis.FakeRedis) -> None:
    assert store.get(redis, "j_nope") is None


def test_update_keeps_ttl_and_validates(redis: fakeredis.FakeRedis) -> None:
    job_id = store.new_job_id()
    store.create(redis, job_id, JobOptions())
    job = store.update(redis, job_id, status="running", stage="transcribing", progress=0.5)
    assert store.get(redis, job_id) == job
    assert job.stage == "transcribing"
    assert redis.ttl(f"job:{job_id}") > 0
    with pytest.raises(ValidationError):
        store.update(redis, job_id, progress=1.5)


def test_update_missing_raises(redis: fakeredis.FakeRedis) -> None:
    with pytest.raises(KeyError):
        store.update(redis, "j_nope", progress=0.1)


def test_timestamps_serialize_as_utc_z(redis: fakeredis.FakeRedis) -> None:
    job = store.create(redis, store.new_job_id(), JobOptions())
    assert job.model_dump(mode="json")["created_at"].endswith("Z")


def test_enqueue(redis: fakeredis.FakeRedis) -> None:
    queue = Queue(connection=redis)
    enqueue(queue, "j_1", "jobs/j_1/input.wav")
    [rq_job] = queue.jobs
    assert rq_job.id == "j_1"
    assert rq_job.func_name == "app.jobs.run.run_job"
    assert rq_job.args == ("j_1", "jobs/j_1/input.wav")
    assert rq_job.timeout == JOB_TIMEOUT_SECONDS
