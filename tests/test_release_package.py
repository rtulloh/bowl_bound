"""Synthetic-only release selection, path safety and build freshness checks."""

import hashlib
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.release_package import (
    ReleaseError,
    assemble_runtime,
    build_frontend,
    stage_sources,
)


def put(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def source(tmp_path: Path) -> Path:
    root = tmp_path / "source with spaces"
    sample = "seasons/2007/cedar-valley/team.yaml"
    files = {
        "bowl_bound/__init__.py": '__version__ = "0.1.0a1"\nDISPLAY_VERSION = "0.1.0-alpha.1"\n',
        "LICENSE": "Synthetic license",
        sample: "Synthetic chart",
        "frontend/package.json": '{"version":"0.1.0-alpha.1"}',
        "frontend/package-lock.json": json.dumps(
            {
                "version": "0.1.0-alpha.1",
                "packages": {"": {"version": "0.1.0-alpha.1"}},
            }
        ),
        "frontend/src/App.jsx": "Synthetic UI",
    }
    for name, text in files.items():
        put(root, name, text)
    manifest = {
        "runtime": ["bowl_bound/__init__.py", "LICENSE", sample],
        "frontend": [name for name in files if name.startswith("frontend/")],
        "sample_sha256": {sample: hashlib.sha256(files[sample].encode()).hexdigest()},
    }
    put(root, "release/manifest.json", json.dumps(manifest))
    for forbidden in (
        "seasons/1900/private-team/team.yaml",
        "seasons/2007/cedar-valley/roster.json",
        "private-data/chart.pdf",
        "docs/dev-notes/private.md",
        "opencode.json",
        ".env",
        "bowl_bound/unapproved.py",
        "frontend/dist/old.js",
    ):
        put(root, forbidden, "DO NOT SHIP")
    return root


def fake_frontend(stage: Path) -> None:
    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if command[-1] == "--version":
            version = "v24.22.1" if command[0] == "node" else "11.19.1"
            return subprocess.CompletedProcess(command, 0, stdout=version)
        if command[-1] == "build":
            put(
                stage,
                "frontend/dist/index.html",
                '<script type="module" src="/assets/index-abc123.js"></script>',
            )
            put(stage, "frontend/dist/assets/index-abc123.js", "Synthetic built UI")
        return subprocess.CompletedProcess(command, 0, stdout="")

    with (
        patch("scripts.release_package.subprocess.run", side_effect=run) as runner,
        patch("scripts.release_package.shutil.which", return_value="npm"),
    ):
        build_frontend(stage)
    assert ["npm", "ci", "--ignore-scripts"] in [call.args[0] for call in runner.call_args_list]


def test_allowlisted_stage_and_runtime_exclude_injected_private_files(
    source: Path, tmp_path: Path
) -> None:
    stage = tmp_path / "build stage"
    stage_sources(source, stage)
    assert not (stage / "frontend/dist").exists()
    assert not any(b"DO NOT SHIP" in p.read_bytes() for p in stage.rglob("*") if p.is_file())
    fake_frontend(stage)
    runtime = tmp_path / "runtime"
    assemble_runtime(stage, runtime)
    found = {p.relative_to(runtime).as_posix() for p in runtime.rglob("*") if p.is_file()}
    assert found == {
        "bowl_bound/__init__.py",
        "LICENSE",
        "seasons/2007/cedar-valley/team.yaml",
        "frontend/dist/index.html",
        "frontend/dist/assets/index-abc123.js",
        "VERSION",
        "MANIFEST.json",
    }
    manifest = json.loads((runtime / "MANIFEST.json").read_text())
    assert manifest["version"] == "0.1.0-alpha.1"
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((runtime / name).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize(
    "name",
    [
        "../secret",
        "/absolute",
        "bowl_bound/../secret",
        "frontend\\secret",
        "C:/secret",
        "bowl_bound/*.py",
    ],
)
def test_invalid_manifest_paths_fail_before_creating_output(
    source: Path, tmp_path: Path, name: str
) -> None:
    manifest = source / "release/manifest.json"
    data = json.loads(manifest.read_text())
    data["runtime"].append(name)
    manifest.write_text(json.dumps(data))
    with pytest.raises(ReleaseError):
        stage_sources(source, tmp_path / "output")
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("path", ["bowl_bound/__init__.py", "bowl_bound", "release/manifest.json"])
def test_symlinked_input_or_parent_is_refused(source: Path, tmp_path: Path, path: str) -> None:
    original = source / path
    moved = tmp_path / "moved"
    original.rename(moved)
    original.symlink_to(moved, target_is_directory=moved.is_dir())
    with pytest.raises(ReleaseError, match="symlink"):
        stage_sources(source, tmp_path / "output")


def test_sample_hash_change_is_not_silently_packaged(source: Path, tmp_path: Path) -> None:
    put(source, "seasons/2007/cedar-valley/team.yaml", "Changed chart")
    with pytest.raises(ReleaseError, match="sample"):
        stage_sources(source, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_missing_input_existing_output_and_symlink_output_parent_are_safe(
    source: Path, tmp_path: Path
) -> None:
    target = tmp_path / "output"
    target.mkdir()
    put(target, "keep", "User work")
    with pytest.raises(ReleaseError):
        stage_sources(source, target)
    assert (target / "keep").read_text() == "User work"
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ReleaseError, match="symlink"):
        stage_sources(source, link / "new")
    (source / "LICENSE").unlink()
    with pytest.raises(ReleaseError):
        stage_sources(source, tmp_path / "missing")
    assert not (tmp_path / "missing").exists()


@pytest.mark.parametrize(
    "mutation", ["missing-build", "source-change", "asset-change", "extra-asset", "symlink-asset"]
)
def test_runtime_refuses_unbuilt_stale_or_unexpected_assets(
    source: Path, tmp_path: Path, mutation: str
) -> None:
    stage = tmp_path / "stage"
    stage_sources(source, stage)
    if mutation != "missing-build":
        fake_frontend(stage)
    if mutation == "source-change":
        put(stage, "frontend/src/App.jsx", "Changed after build")
    elif mutation == "asset-change":
        put(stage, "frontend/dist/assets/index-abc123.js", "Changed after build")
    elif mutation == "extra-asset":
        put(stage, "frontend/dist/private.log", "Do not ship")
    elif mutation == "symlink-asset":
        asset = stage / "frontend/dist/assets/index-abc123.js"
        asset.unlink()
        asset.symlink_to(source / "LICENSE")
    with pytest.raises(ReleaseError):
        assemble_runtime(stage, tmp_path / "runtime")
    assert not (tmp_path / "runtime").exists()


def test_preexisting_frontend_dist_and_wrong_node_are_refused(source: Path, tmp_path: Path) -> None:
    stage = tmp_path / "stage"
    stage_sources(source, stage)
    put(stage, "frontend/dist/index.html", "Stale")
    with pytest.raises(ReleaseError, match="dist"):
        build_frontend(stage)
    (stage / "frontend/dist/index.html").unlink()
    (stage / "frontend/dist").rmdir()
    with patch("scripts.release_package.subprocess.run") as runner:
        runner.return_value.stdout = "v18.0.0"
        with pytest.raises(ReleaseError, match="24.22.1"):
            build_frontend(stage)


@pytest.mark.parametrize("packages", [None, [], {"": None}, {"": []}])
def test_malformed_frontend_metadata_is_actionable(
    source: Path, tmp_path: Path, packages: object
) -> None:
    put(
        source,
        "frontend/package-lock.json",
        json.dumps(
            {
                "version": "0.1.0-alpha.1",
                "packages": packages,
            }
        ),
    )
    with pytest.raises(ReleaseError, match="version"):
        stage_sources(source, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_failed_frontend_command_cannot_issue_build_receipt(source: Path, tmp_path: Path) -> None:
    stage = tmp_path / "stage"
    stage_sources(source, stage)

    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if command[-1] == "--version":
            version = "v24.22.1" if command[0] == "node" else "11.19.1"
            return subprocess.CompletedProcess(command, 0, stdout=version)
        raise subprocess.CalledProcessError(1, command)

    with patch("scripts.release_package.subprocess.run", side_effect=run):
        with pytest.raises(subprocess.CalledProcessError):
            build_frontend(stage)
    assert not (stage / "frontend-build.json").exists()
