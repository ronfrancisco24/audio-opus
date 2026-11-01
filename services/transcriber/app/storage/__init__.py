from pathlib import Path
from typing import Protocol


class Storage(Protocol):
    """Job files by key, e.g. `jobs/{id}/score.musicxml`. Keys are partly user-derived."""

    def put(self, key: str, data: bytes | Path) -> None: ...

    def get(self, key: str) -> Path: ...

    def exists(self, key: str) -> bool: ...

    def delete_prefix(self, prefix: str) -> None: ...
