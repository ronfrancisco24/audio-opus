from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from redis import Redis
from rq import Queue

from app.config import settings
from app.storage import Storage
from app.storage.local import LocalStorage


@lru_cache
def get_redis() -> Redis:
    return Redis.from_url(settings.redis_url)


def get_queue(redis: Annotated[Redis, Depends(get_redis)]) -> Queue:
    return Queue(connection=redis)


@lru_cache
def get_storage() -> Storage:
    if settings.storage_backend != "local":
        raise NotImplementedError("S3 storage arrives in phase 3")
    return LocalStorage(settings.storage_local_dir)


RedisDep = Annotated[Redis, Depends(get_redis)]
QueueDep = Annotated[Queue, Depends(get_queue)]
StorageDep = Annotated[Storage, Depends(get_storage)]
