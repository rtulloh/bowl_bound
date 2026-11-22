"""Browser archive tests use synthetic source and runtime files."""

import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from scripts import build_browser_bundle as browser
from scripts.release_package import SAMPLES, ReleaseError, _sha


@pytest.fixture
def inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    source = tmp_path / "source"
    runtime = tmp_path / "pinned-runtime"
    runtime.mkdir()
    asset = b"synthetic runtime"
    (runtime / "pyodide.mjs").write_bytes(asset)
    monkeypatch.setattr(browser, "RUNTIME_HASHES", {"pyodide.mjs": _sha(asset)})
    hashes = {}
    for name in SAMPLES | browser.PYTHON_FILES:
        content = name.encode()
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        if name in SAMPLES:
            hashes[name] = _sha(content)
    release = source / "release"
    release.mkdir()
    (release / "manifest.json").write_text(
        json.dumps({"sample_sha256": hashes, "runtime": sorted(SAMPLES)}), encoding="utf-8"
    )
    private = source / "seasons/2007/cedar-valley/private.yaml"
    private.write_text("must stay private", encoding="utf-8")
    return source, runtime


def test_stage_exact_reproducible_public_inventory(
    inputs: tuple[Path, Path], tmp_path: Path
) -> None:
    source, runtime = inputs
    output = tmp_path / "public"
    manifest = browser.build_bundle(source, output, runtime_dir=runtime)
    assert manifest == browser.build_bundle(source, tmp_path / "again", runtime_dir=runtime)
    assert manifest["seasons"] == {"2007": ["cedar-valley", "harbor-tech"]}
    archive = output / "python.zip"
    assert manifest["files"][0]["sha256"] == _sha(archive.read_bytes())
    with ZipFile(archive) as bundle:
        assert set(bundle.namelist()) == SAMPLES | browser.PYTHON_FILES
        assert all(
            item["sha256"] == _sha(bundle.read(item["path"])) for item in manifest["inventory"]
        )
    assert [file.name for file in (output / "pyodide").iterdir()] == ["pyodide.mjs"]


@pytest.mark.parametrize("mutation", ["sample-digest", "sample-symlink", "runtime-digest"])
def test_invalid_inputs_leave_no_staging_directory(
    inputs: tuple[Path, Path], tmp_path: Path, mutation: str
) -> None:
    source, runtime = inputs
    sample = source / "seasons/2007/cedar-valley/team.yaml"
    if mutation == "sample-digest":
        sample.write_text("changed chart", encoding="utf-8")
    elif mutation == "sample-symlink":
        target = sample.with_name("private.yaml")
        target.write_bytes(sample.read_bytes())
        sample.unlink()
        sample.symlink_to(target)
    else:
        (runtime / "pyodide.mjs").write_bytes(b"changed runtime")
    output = tmp_path / "public"
    with pytest.raises(ReleaseError, match="hash mismatch|symlinks"):
        browser.build_bundle(source, output, runtime_dir=runtime)
    assert not output.exists()


def test_stage_refuses_to_overwrite_existing_output(
    inputs: tuple[Path, Path], tmp_path: Path
) -> None:
    source, runtime = inputs
    output = tmp_path / "public"
    output.mkdir()
    private = output / "unrelated.txt"
    private.write_text("preserve existing content", encoding="utf-8")
    with pytest.raises(ReleaseError, match="already exists"):
        browser.build_bundle(source, output, runtime_dir=runtime)
    assert private.read_text(encoding="utf-8") == "preserve existing content"
