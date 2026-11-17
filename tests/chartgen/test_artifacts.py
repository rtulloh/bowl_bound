"""Complete fictional report storage, deterministic compression and disk budgets."""

import gzip
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.chartgen.artifacts import (
    ArtifactCompression,
    StorageCapacityError,
    check_capacity,
    read_artifact,
    write_artifact,
)


def test_complete_report_gzip_is_lossless_deterministic_and_never_overwritten(
    tmp_path: Path,
) -> None:
    payload = {
        "result_sha256": "fictional-semantic-checksum",
        "result": {
            "engine_log": [{"trace": ["observed fictional roll"], "yards": 4}] * 100,
            "save": {"commands": ["fictional command"], "team": "Cedar Valley"},
        },
    }
    first, second = tmp_path / "first.json.gz", tmp_path / "second.json.gz"
    for path in (first, second):
        write_artifact(path, payload, compression=ArtifactCompression.GZIP)
        assert read_artifact(path) == payload
    assert first.read_bytes() == second.read_bytes()
    assert len(first.read_bytes()) < len(json.dumps(payload)) / 4
    original = first.read_bytes()
    with pytest.raises(FileExistsError):
        write_artifact(first, {"changed": True}, compression=ArtifactCompression.GZIP)
    assert first.read_bytes() == original
    assert not list(tmp_path.glob(".pending-*"))


def test_legacy_plain_json_remains_readable_and_new_plain_json_is_complete(tmp_path: Path) -> None:
    legacy = tmp_path / "legacy.json"
    legacy.write_text('{"result": {"score": 7, "trace": ["fictional"]}}')
    payload = read_artifact(legacy)
    copied = tmp_path / "copied.json"
    write_artifact(copied, payload)
    assert json.loads(copied.read_text()) == payload


@pytest.mark.parametrize("kind", ["truncated-gzip", "invalid-gzip", "truncated-json"])
def test_corrupt_or_incomplete_artifacts_fail_without_repair(tmp_path: Path, kind: str) -> None:
    compressed = kind != "truncated-json"
    path = tmp_path / ("report.json.gz" if compressed else "report.json")
    data = gzip.compress(b'{"complete": true}', mtime=0)
    bad = data[:-8] if kind == "truncated-gzip" else b"invalid" if compressed else b'{"result":'
    path.write_bytes(bad)
    with pytest.raises(ValueError, match="corrupt or incomplete"):
        read_artifact(path)
    assert path.read_bytes() == bad


def test_failed_serialization_does_not_publish_or_leave_partial_files(tmp_path: Path) -> None:
    path = tmp_path / "report.json.gz"
    with pytest.raises(ValueError):
        write_artifact(path, {"unknown": float("nan")}, compression=ArtifactCompression.GZIP)
    assert not path.exists() and not list(tmp_path.iterdir())


def test_capacity_check_records_budget_and_rejects_before_engine_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tools.chartgen import artifacts

    monkeypatch.setattr(
        artifacts.shutil, "disk_usage", lambda _: SimpleNamespace(free=20 * 1024**3)
    )
    record = check_capacity(tmp_path / "new", 704, compression=ArtifactCompression.GZIP)
    assert record["requested_game_reports"] == 704
    assert record["estimated_artifact_bytes"] >= 704 * 256 * 1024
    assert record["reserve_bytes"] == 3 * 1024**3
    monkeypatch.setattr(artifacts.shutil, "disk_usage", lambda _: SimpleNamespace(free=1024))
    with pytest.raises(StorageCapacityError, match="insufficient storage"):
        check_capacity(tmp_path / "new", 704, compression=ArtifactCompression.GZIP)
    assert not (tmp_path / "new").exists()
    assert check_capacity(tmp_path, 0)["requested_game_reports"] == 0
