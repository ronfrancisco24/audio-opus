from pathlib import Path

import fakeredis
import httpx
import pytest
from fastapi.testclient import TestClient
from rq import Queue

from app.api.schemas import JobOptions
from app.config import settings
from app.jobs import store
from app.storage.local import LocalStorage
from tests.conftest import FIXTURES

SCALE = FIXTURES / "synth_c_major_scale_8s.wav"


def upload(client: TestClient, path: Path = SCALE, **form: str) -> httpx.Response:
    with path.open("rb") as f:
        return client.post("/jobs", files={"file": (path.name, f, "audio/wav")}, data=form)


def assert_error(response: httpx.Response, status: int, code: str) -> None:
    assert response.status_code == status, response.text
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["message"]


def test_create_job_happy_path(client: TestClient, queue: Queue, storage: LocalStorage) -> None:
    response = upload(client, instrument="piano")
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued" and body["id"].startswith("j_")

    input_key = f"jobs/{body['id']}/input.wav"
    assert storage.get(input_key).read_bytes() == SCALE.read_bytes()
    assert queue.jobs[0].args == (body["id"], input_key)

    job = client.get(f"/jobs/{body['id']}").json()
    assert job["status"] == "queued"
    assert job["options"] == {"instrument": "piano", "mode": "solo", "title": SCALE.stem}
    assert job["result"] is None and job["error"] is None


def test_content_type_used_when_extension_missing(
    client: TestClient, storage: LocalStorage
) -> None:
    response = client.post(
        "/jobs", files={"file": ("blob", b"\x1aE", "audio/webm;codecs=opus")}, data={"title": "Rec"}
    )
    assert response.status_code == 202
    assert storage.exists(f"jobs/{response.json()['id']}/input.webm")


def test_wrong_type(client: TestClient) -> None:
    response = client.post("/jobs", files={"file": ("notes.txt", b"hi", "text/plain")})
    assert_error(response, 400, "UNSUPPORTED_FORMAT")


def test_invalid_option(client: TestClient) -> None:
    assert_error(upload(client, instrument="kazoo"), 400, "INVALID_REQUEST")


def test_full_song_not_available(client: TestClient) -> None:
    assert_error(upload(client, mode="full_song"), 400, "INVALID_REQUEST")


def test_missing_file(client: TestClient) -> None:
    assert_error(client.post("/jobs", data={"title": "x"}), 400, "INVALID_REQUEST")


def test_too_large(client: TestClient, queue: Queue, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "max_upload_mb", 0)
    assert_error(upload(client), 413, "FILE_TOO_LARGE")
    assert queue.count == 0


def test_unknown_job(client: TestClient) -> None:
    assert_error(client.get("/jobs/j_nope"), 404, "NOT_FOUND")


def test_artifact_download(
    client: TestClient, redis: fakeredis.FakeRedis, storage: LocalStorage
) -> None:
    store.create(redis, "j_1", JobOptions())
    storage.put("jobs/j_1/score.musicxml", b"<score-partwise/>")
    response = client.get("/jobs/j_1/artifacts/score.musicxml")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.recordare.musicxml+xml"
    assert response.content == b"<score-partwise/>"


@pytest.mark.parametrize("name", ["../x", "..%2Fx", "input.wav", "score.pdf"])
def test_artifact_rejected_or_missing(
    client: TestClient, redis: fakeredis.FakeRedis, storage: LocalStorage, name: str
) -> None:
    store.create(redis, "j_1", JobOptions())
    storage.put("jobs/j_1/input.wav", b"RIFF")
    assert_error(client.get(f"/jobs/j_1/artifacts/{name}"), 404, "NOT_FOUND")


def test_artifact_unknown_job(client: TestClient) -> None:
    assert_error(client.get("/jobs/j_nope/artifacts/score.musicxml"), 404, "NOT_FOUND")
