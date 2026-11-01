import os
from collections.abc import Iterator
from pathlib import Path

import fakeredis
import pytest
from fastapi.testclient import TestClient
from rq import Queue

from app.api.deps import get_queue, get_redis, get_storage
from app.main import app
from app.storage.local import LocalStorage

# In Docker the repo's fixtures/ is mounted at FIXTURES_DIR; natively it's three levels up.
FIXTURES = Path(os.environ.get("FIXTURES_DIR", Path(__file__).parents[3] / "fixtures"))


@pytest.fixture
def redis() -> fakeredis.FakeRedis:
    return fakeredis.FakeRedis()


@pytest.fixture
def queue(redis: fakeredis.FakeRedis) -> Queue:
    return Queue(connection=redis)


@pytest.fixture
def storage(tmp_path: Path) -> LocalStorage:
    return LocalStorage(tmp_path / "data")


@pytest.fixture
def client(redis: fakeredis.FakeRedis, queue: Queue, storage: LocalStorage) -> Iterator[TestClient]:
    app.dependency_overrides[get_redis] = lambda: redis
    app.dependency_overrides[get_queue] = lambda: queue
    app.dependency_overrides[get_storage] = lambda: storage
    yield TestClient(app)
    app.dependency_overrides.clear()
