from pathlib import Path

import pytest

from app.storage.local import LocalStorage


def test_put_get_round_trip(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    storage.put("jobs/j_1/input.wav", b"abc")
    assert storage.exists("jobs/j_1/input.wav")
    assert storage.get("jobs/j_1/input.wav").read_bytes() == b"abc"


def test_put_copies_path(tmp_path: Path) -> None:
    src = tmp_path / "src.mid"
    src.write_bytes(b"MThd")
    storage = LocalStorage(tmp_path / "data")
    storage.put("jobs/j_1/transcription.mid", src)
    assert storage.get("jobs/j_1/transcription.mid").read_bytes() == b"MThd"


def test_get_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        LocalStorage(tmp_path).get("jobs/nope/score.musicxml")


def test_delete_prefix(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    storage.put("jobs/j_1/a.wav", b"a")
    storage.put("jobs/j_2/a.wav", b"b")
    storage.delete_prefix("jobs/j_1")
    assert not storage.exists("jobs/j_1/a.wav")
    assert storage.exists("jobs/j_2/a.wav")


@pytest.mark.parametrize("key", ["../x", "jobs/../../x", "/etc/passwd", "\\x", "", "jobs/j_1/.."])
def test_rejects_traversal_keys(tmp_path: Path, key: str) -> None:
    with pytest.raises(ValueError):
        LocalStorage(tmp_path / "data").put(key, b"x")
