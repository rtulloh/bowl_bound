"""Native recipes and archive guards use synthetic runtime inputs only."""

import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from scripts import build_standalone as native
from scripts.release_package import ReleaseError, assemble_runtime, stage_sources
from tests.test_release_package import fake_frontend, put
from tests.test_release_package import source as source_fixture

source = source_fixture


@pytest.fixture
def runtime(source: Path, tmp_path: Path) -> Path:
    stage = tmp_path / "stage"
    stage_sources(source, stage)
    fake_frontend(stage)
    root = tmp_path / "runtime"
    assemble_runtime(stage, root)
    return root


@pytest.mark.parametrize(
    ("target", "system", "machine", "executable"),
    [
        ("macos-arm64", "Darwin", "arm64", "Bowl-Bound"),
        ("macos-x86_64", "Darwin", "x86_64", "Bowl-Bound"),
        ("windows-x64", "Windows", "AMD64", "BowlBound.exe"),
    ],
)
def test_target_requires_matching_native_architecture(
    target: str, system: str, machine: str, executable: str
) -> None:
    assert native.check_target(target, system, machine) == executable
    with pytest.raises(ReleaseError, match="native"):
        native.check_target(target, "Linux", "x86_64")
    with pytest.raises(ReleaseError, match="native"):
        native.check_target(target, system, "i386")


def test_unknown_target_is_not_an_implicit_linux_build() -> None:
    with pytest.raises(ReleaseError, match="target"):
        native.check_target("linux-x64", "Linux", "x86_64")


def test_spec_uses_only_verified_staged_resources(runtime: Path, tmp_path: Path) -> None:
    work = tmp_path / "freezer"
    work.mkdir()
    spec = native.write_spec(runtime, work, "macos-arm64")
    text = spec.read_text()
    assert str(runtime) in text and "backend.launcher" in (work / "entry.py").read_text()
    assert "uvicorn.protocols.http.h11_impl" in text
    assert "uvicorn.lifespan.on" in text and "uvicorn.loops.asyncio" in text
    assert "collect_all" not in text and "onefile" not in text
    assert "console=True" in text and "upx=False" in text
    assert "optimize=0" in text  # retain engine assertions, as in normal source execution
    assert "bowl_bound/__init__.py" not in text  # code is analyzed, never copied as data
    assert "seasons/2007/cedar-valley" in text.replace("\\", "/")
    assert "private-data" not in text and "opencode.json" not in text


@pytest.mark.parametrize("mutation", ["extra", "changed"])
def test_stale_or_injected_runtime_is_refused_before_freezing(
    runtime: Path, tmp_path: Path, mutation: str
) -> None:
    if mutation == "extra":
        put(runtime, "private-data/chart.pdf", "DO NOT SHIP")
    else:
        put(runtime, "LICENSE", "changed")
    work = tmp_path / "freezer"
    work.mkdir()
    with pytest.raises(ReleaseError):
        native.write_spec(runtime, work, "macos-arm64")
    assert not (work / "entry.py").exists()


def fake_bundle(runtime: Path, path: Path) -> Path:
    import shutil

    path.mkdir()
    put(path, "Bowl-Bound", "Synthetic executable")
    for name in json.loads((runtime / "MANIFEST.json").read_text())["files"]:
        if not name.endswith(".py"):
            target = path / "_internal" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(runtime / name, target)
    return path


def test_archive_checksums_exact_manifest_and_safe_extraction(
    runtime: Path, tmp_path: Path
) -> None:
    bundle = fake_bundle(runtime, tmp_path / "bundle")
    output = tmp_path / "output"
    output.mkdir()
    archive = native.archive_bundle(bundle, runtime, output, "macos-arm64")
    assert archive.name == "BowlBound-0.1.0-alpha.1-macos-arm64.zip"
    checksum = archive.with_suffix(".zip.sha256").read_text().strip().split()
    assert checksum == [hashlib.sha256(archive.read_bytes()).hexdigest(), archive.name]
    with ZipFile(archive) as zipped:
        names = zipped.namelist()
        assert len(names) == len(set(names))
        manifest = json.loads(zipped.read("BowlBound/ARTIFACT-MANIFEST.json"))
        assert manifest["target"] == "macos-arm64"
        for name, digest in manifest["files"].items():
            assert hashlib.sha256(zipped.read("BowlBound/" + name)).hexdigest() == digest
    with pytest.raises(ReleaseError):
        native.archive_bundle(bundle, runtime, output, "macos-arm64")


@pytest.mark.parametrize(
    "name",
    [
        "_internal/private-data/chart.pdf",
        "_internal/seasons/1900/team.yaml",
        "_internal/seasons/2007/cedar-valley/roster.json",
        "opencode.json",
    ],
)
def test_native_archive_refuses_private_or_unselected_data(
    runtime: Path, tmp_path: Path, name: str
) -> None:
    bundle = fake_bundle(runtime, tmp_path / "bundle")
    put(bundle, name, "DO NOT SHIP")
    output = tmp_path / "output"
    output.mkdir()
    with pytest.raises(ReleaseError):
        native.archive_bundle(bundle, runtime, output, "macos-arm64")
    assert not list(output.iterdir())


def test_archive_refuses_modified_public_resources(runtime: Path, tmp_path: Path) -> None:
    bundle = fake_bundle(runtime, tmp_path / "bundle")
    put(bundle, "_internal/LICENSE", "modified after assembly")
    output = tmp_path / "output"
    output.mkdir()
    with pytest.raises(ReleaseError, match="resource"):
        native.archive_bundle(bundle, runtime, output, "macos-arm64")


def test_materialization_refuses_links_outside_freezer_output(tmp_path: Path) -> None:
    original = tmp_path / "original"
    original.mkdir()
    put(tmp_path, "private.txt", "DO NOT SHIP")
    (original / "escape").symlink_to(tmp_path / "private.txt")
    with pytest.raises(ReleaseError, match="symlink"):
        native.materialize(original, tmp_path / "copy")


@pytest.mark.parametrize("installed", [False, True])
def test_environment_ignores_checkout_metadata_but_refuses_installed_project(
    source: Path, monkeypatch: pytest.MonkeyPatch, installed: bool
) -> None:
    from types import SimpleNamespace

    put(source, "release/requirements-native.txt", "")
    monkeypatch.setattr(
        native.metadata, "distribution", lambda name: SimpleNamespace(name="bowl_bound")
    )
    monkeypatch.setattr(
        native.metadata,
        "distributions",
        lambda **kwargs: [SimpleNamespace(metadata={"Name": "bowl-bound"})] if installed else [],
    )
    if installed:
        with pytest.raises(ReleaseError, match="clean build environment"):
            native.verify_environment(source)
    else:
        native.verify_environment(source)


@pytest.mark.parametrize("import_process", ["analysis", "hook-child"])
def test_freezer_imports_cannot_mutate_verified_runtime(
    source: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, import_process: str
) -> None:
    """Run real isolated imports through a synthetic freezer, without PyInstaller."""
    import subprocess

    run = subprocess.run
    monkeypatch.delenv("PYTHONDONTWRITEBYTECODE", raising=False)
    monkeypatch.setattr(native, "check_target", lambda *args: "BowlBound.exe")
    monkeypatch.setattr(native, "verify_environment", lambda source: None)
    monkeypatch.setattr(native, "build_frontend", fake_frontend)
    monkeypatch.setattr(native, "write_notices", lambda stage, destination: destination.mkdir())

    def freeze(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        work = Path(kwargs["cwd"])
        runtime = work / "runtime"
        probe = f"import sys; sys.path.insert(0, {str(runtime)!r}); import bowl_bound"
        if import_process == "hook-child":
            # PyInstaller 6.22.3 hook children inherit env, not parent -I/-B flags.
            probe = (
                "import subprocess, sys; "
                f"subprocess.run([sys.executable, '-c', {probe!r}], check=True)"
            )
        result = run(
            [command[0], *command[1 : command.index("-m")], "-c", probe],
            **kwargs,
        )
        dist = work / "dist"
        dist.mkdir()
        frozen = fake_bundle(runtime, dist / "BowlBound")
        (frozen / "Bowl-Bound").rename(frozen / "BowlBound.exe")
        return result

    def inspect(executable: Path, runtime: Path) -> None:
        native._runtime_files(runtime)
        assert not list(runtime.rglob("*.pyc"))

    monkeypatch.setattr(native.subprocess, "run", freeze)
    monkeypatch.setattr(native, "inspect_modules", inspect)
    output = tmp_path / "native output"
    native.build(source, output, "windows-x64")
    archive = output / "BowlBound-0.1.0-alpha.1-windows-x64.zip"
    with ZipFile(archive) as zipped:
        assert "BowlBound/BowlBound.exe" in zipped.namelist()
        assert not any("__pycache__" in name for name in zipped.namelist())
