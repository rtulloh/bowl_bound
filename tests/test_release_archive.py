"""Archive inspections use only the synthetic packaging source fixture."""

from pathlib import Path
from zipfile import ZipFile

import pytest

from scripts.release_package import ReleaseError, archive_runtime, assemble_runtime, stage_sources
from tests.test_release_package import fake_frontend, put
from tests.test_release_package import source as source_fixture

source = source_fixture


def test_archive_inspection_and_reproducible_content(source: Path, tmp_path: Path) -> None:
    stage = tmp_path / "stage"
    runtime = tmp_path / "runtime"
    stage_sources(source, stage)
    fake_frontend(stage)
    assemble_runtime(stage, runtime)
    first, second = tmp_path / "first.zip", tmp_path / "second.zip"
    archive_runtime(runtime, first)
    archive_runtime(runtime, second)
    assert first.read_bytes() == second.read_bytes()
    with ZipFile(first) as archive:
        assert all(n.startswith("Bowl-Bound-0.1.0-alpha.1/") for n in archive.namelist())
        assert not any(b"DO NOT SHIP" in archive.read(n) for n in archive.namelist())
        for name in archive.namelist():
            assert archive.read(name) == (runtime / name.split("/", 1)[1]).read_bytes()
    with pytest.raises(ReleaseError):
        archive_runtime(runtime, first)
    assert first.read_bytes() == second.read_bytes()


@pytest.mark.parametrize("mutation", ["extra-file", "changed-file", "symlink"])
def test_archive_rejects_injected_files_and_does_not_create_output(
    source: Path, tmp_path: Path, mutation: str
) -> None:
    stage, runtime = tmp_path / "stage", tmp_path / "runtime"
    stage_sources(source, stage)
    fake_frontend(stage)
    assemble_runtime(stage, runtime)
    if mutation == "extra-file":
        put(runtime, "private-data/injected.pdf", "DO NOT SHIP")
    elif mutation == "changed-file":
        put(runtime, "LICENSE", "Changed after assembly")
    else:
        (runtime / "LICENSE").unlink()
        (runtime / "LICENSE").symlink_to(source / "LICENSE")
    output = tmp_path / "release.zip"
    with pytest.raises(ReleaseError):
        archive_runtime(runtime, output)
    assert not output.exists()
