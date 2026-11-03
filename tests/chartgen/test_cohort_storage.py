"""Real-engine fictional cohort artifacts retain strict compressed resume checks."""

import gzip
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.chartgen.artifacts import ArtifactCompression, StorageCapacityError, read_artifact
from tools.chartgen.cohort_simulation import run_historical_batch

from .test_cohort_simulation import prepared


def test_real_engine_gzip_resume_preserves_complete_evidence_and_rejects_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tools.chartgen import artifacts, cohort_simulation

    report, targets, catalog, teams = prepared(tmp_path)
    output = tmp_path / "private-data" / "compressed"
    options = {
        "repetitions": 1,
        "master_seed": 77,
        "domain": "heldout",
        "verify_replay": True,
        "compression": ArtifactCompression.GZIP,
    }
    result = run_historical_batch(report, teams, catalog, targets, output, **options)
    assert result["failed_games"] == 0 and result["passed_games"] == 2
    paths = sorted(output.glob("game-*.json.gz"))
    assert len(paths) == 2 and not list(output.glob("game-*.json"))
    assert result["artifact_storage"]["complete_artifact_bytes"] == sum(
        p.stat().st_size for p in paths
    )
    assert result["artifact_storage"]["compression"] == "gzip"
    first = paths[0].read_bytes()
    payload = read_artifact(paths[0])
    assert payload["result"]["engine_log"] and payload["result"]["coaching_calls"]
    second = paths[1].read_bytes()
    paths[1].unlink()
    assert (
        run_historical_batch(report, teams, catalog, targets, output, resume=True, **options)
        == result
    )
    assert paths[0].read_bytes() == first and paths[1].read_bytes() == second
    monkeypatch.setattr(artifacts.shutil, "disk_usage", lambda _: SimpleNamespace(free=1024))
    monkeypatch.setattr(
        cohort_simulation, "_execute_run", lambda _: pytest.fail("unexpected replay")
    )
    assert (
        run_historical_batch(report, teams, catalog, targets, output, resume=True, **options)
        == result
    )
    assert paths[0].read_bytes() == first
    payload["result"]["final"]["home_score"] += 1
    paths[0].write_bytes(gzip.compress(json.dumps(payload).encode(), mtime=0))
    with pytest.raises(ValueError, match="checksum"):
        run_historical_batch(report, teams, catalog, targets, output, resume=True, **options)
    paths[0].write_bytes(gzip.compress(b"[]", mtime=0))
    with pytest.raises(ValueError, match="contract"):
        run_historical_batch(report, teams, catalog, targets, output, resume=True, **options)
    paths[0].write_bytes(first[:-8])
    with pytest.raises(ValueError, match="corrupt or incomplete"):
        run_historical_batch(report, teams, catalog, targets, output, resume=True, **options)
    assert paths[0].read_bytes() == first[:-8]


def test_insufficient_storage_never_starts_engine_or_creates_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tools.chartgen import artifacts, cohort_simulation

    report, targets, catalog, teams = prepared(tmp_path)
    monkeypatch.setattr(artifacts.shutil, "disk_usage", lambda _: SimpleNamespace(free=1024))
    monkeypatch.setattr(cohort_simulation, "_execute_run", lambda _: pytest.fail("engine started"))
    output = tmp_path / "private-data" / "too-large"
    with pytest.raises(StorageCapacityError, match="insufficient storage"):
        run_historical_batch(
            report,
            teams,
            catalog,
            targets,
            output,
            repetitions=1,
            master_seed=77,
            domain="training",
            compression=ArtifactCompression.GZIP,
        )
    assert not output.exists()
