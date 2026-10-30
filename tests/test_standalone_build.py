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
    assert archive.name == "BowlBound-0.1.0-alpha.2-macos-arm64.zip"
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
    # This regression isolates Python import side effects, not native notice collection.
    monkeypatch.setattr(native, "add_native_notices", lambda *args, **kwargs: None)

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
    archive = output / "BowlBound-0.1.0-alpha.2-windows-x64.zip"
    with ZipFile(archive) as zipped:
        assert "BowlBound/BowlBound.exe" in zipped.namelist()
        assert not any("__pycache__" in name for name in zipped.namelist())


@pytest.mark.parametrize("target", ["macos-arm64", "macos-x86_64", "windows-x64"])
def test_archive_refuses_native_payload_without_notices(
    runtime: Path, tmp_path: Path, target: str
) -> None:
    bundle = fake_bundle(runtime, tmp_path / "bundle")
    if target == "windows-x64":
        (bundle / "Bowl-Bound").rename(bundle / "BowlBound.exe")
        (bundle / "BowlBound.exe").write_bytes(b"MZsynthetic PE executable")
    else:
        (bundle / "Bowl-Bound").write_bytes(b"\xcf\xfa\xed\xfeSynthetic Mach-O")
    output = tmp_path / "output"
    output.mkdir()
    with pytest.raises(ReleaseError, match="native notice"):
        native.archive_bundle(bundle, runtime, output, target)
    assert not list(output.iterdir())


def test_notices_include_analyzed_packaging_and_setuptools_vendor_licenses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    stage = tmp_path / "stage"
    for name in ("react", "react-dom", "scheduler"):
        put(stage, f"frontend/node_modules/{name}/package.json", '{"version":"1.0.0"}')
        put(stage, f"frontend/node_modules/{name}/LICENSE", "Synthetic frontend permission")
    python = tmp_path / "python"
    put(python, "LICENSE.txt", "Synthetic Python permission")
    monkeypatch.setattr(native.sysconfig, "get_path", lambda name: str(python))

    def distribution(name: str) -> SimpleNamespace:
        root = tmp_path / "installed" / name
        put(root, "LICENSE", f"Synthetic {name} permission")
        files = [Path("LICENSE")]
        if name == "setuptools":
            vendor = "_vendor/fake.dist-info/LICENSE"
            put(root, vendor, "Synthetic vendored permission")
            files.append(Path(vendor))
        return SimpleNamespace(files=files, locate_file=lambda p: root / p, version="1.0.0")

    monkeypatch.setattr(native.metadata, "distribution", distribution)
    destination = tmp_path / "notices"
    native.write_notices(stage, destination)
    inventory = json.loads((destination / "DEPENDENCIES.json").read_text())
    assert {"setuptools", "packaging"} <= inventory.keys()
    assert len(inventory["setuptools"]["notices"]) == 2
    assert any(
        (destination / path).read_text() == "Synthetic vendored permission"
        for path in inventory["setuptools"]["notices"]
    )


@pytest.mark.parametrize("target", ["macos-arm64", "macos-x86_64", "windows-x64"])
def test_native_archive_and_installer_include_exact_notice_bytes(
    runtime: Path, tmp_path: Path, target: str
) -> None:
    from scripts.native_notices import add_native_notices
    from scripts.smoke_standalone import extract_verified
    from scripts.windows_installer import write_file_lists

    bundle = fake_bundle(runtime, tmp_path / "bundle")
    executable = "BowlBound.exe" if target == "windows-x64" else "Bowl-Bound"
    if target == "windows-x64":
        (bundle / "Bowl-Bound").rename(bundle / executable)
    (bundle / executable).write_bytes(
        b"MZsynthetic" if target == "windows-x64" else b"\xcf\xfa\xed\xfe"
    )
    notice = "Synthetic native copyright and permission\n"
    source = tmp_path / "notice source"
    put(source, "release/native-notices/bootloader.txt", notice)
    catalog = {
        "schema": 1,
        "python": "3.13.17",
        "notices": {
            "bootloader.txt": {
                "sha256": hashlib.sha256(notice.encode()).hexdigest(),
                "source": "https://example.org/synthetic/LICENSE",
            }
        },
        "components": {
            "pyinstaller": {
                "version": "1.0",
                "notices": ["bootloader.txt"],
                "provenance": "Synthetic fixture",
            }
        },
    }
    put(source, "release/native-notices/manifest.json", json.dumps(catalog))
    add_native_notices(source, bundle, target, python_version="3.13.17")
    output = tmp_path / "output"
    output.mkdir()
    archive = native.archive_bundle(bundle, runtime, output, target)
    extracted = tmp_path / "extracted"
    report = extract_verified(archive, extracted)
    for prefix in ("THIRD_PARTY", "_internal/THIRD_PARTY"):
        name = prefix + "/NATIVE/bootloader.txt"
        assert report["files"][name] == hashlib.sha256(notice.encode()).hexdigest()
        assert (extracted / "BowlBound" / name).read_bytes() == notice.encode()
    if target == "windows-x64":
        work = tmp_path / "installer"
        work.mkdir()
        write_file_lists(extracted / "BowlBound", work)
        install = (work / "install-files.nsh").read_text()
        uninstall = (work / "uninstall-files.nsh").read_text()
        for prefix in ("THIRD_PARTY", "_internal/THIRD_PARTY"):
            path = prefix.replace("/", "\\") + "\\NATIVE\\bootloader.txt"
            assert path in uninstall
        assert install.count('File "/oname=bootloader.txt"') == 2
        assert "RMDir /r" not in uninstall


@pytest.fixture
def roster_runtime(source: Path, tmp_path: Path) -> Path:
    """Stage invented, hash-pinned rosters through the real sample selector."""
    manifest_path = source / "release/manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for team in ("cedar-valley", "harbor-tech"):
        for filename, text in (
            ("roster.json", '{"qb":["Synthetic Quill"],"wr":["Synthetic Finch"]}\n'),
            ("roster-sources.md", "Original synthetic test names, CC0-1.0\n"),
        ):
            name = f"seasons/2007/{team}/{filename}"
            put(source, name, text)
            manifest["runtime"].append(name)
            manifest["sample_sha256"][name] = hashlib.sha256(text.encode()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    stage = tmp_path / "roster-stage"
    stage_sources(source, stage)
    fake_frontend(stage)
    destination = tmp_path / "roster-runtime"
    assemble_runtime(stage, destination)
    return destination


@pytest.mark.parametrize("target", list(native.TARGETS))
def test_native_sample_rosters_survive_archive_extraction_and_installer(
    roster_runtime: Path, tmp_path: Path, target: str
) -> None:
    from scripts.smoke_standalone import extract_verified
    from scripts.windows_installer import write_file_lists

    bundle = fake_bundle(roster_runtime, tmp_path / "bundle")
    executable = native.TARGETS[target][2]
    if executable != "Bowl-Bound":
        (bundle / "Bowl-Bound").rename(bundle / executable)
    output = tmp_path / "output"
    output.mkdir()
    archive = native.archive_bundle(bundle, roster_runtime, output, target)
    destination = tmp_path / "extracted"
    report = extract_verified(archive, destination)
    roster_paths = {
        f"_internal/seasons/2007/{team}/{filename}"
        for team in ("cedar-valley", "harbor-tech")
        for filename in ("roster.json", "roster-sources.md")
    }
    assert {name for name in report["files"] if "roster" in name} == roster_paths
    for name in roster_paths:
        expected = (roster_runtime / name.removeprefix("_internal/")).read_bytes()
        assert (destination / "BowlBound" / name).read_bytes() == expected
        assert report["files"][name] == hashlib.sha256(expected).hexdigest()
    if target == "windows-x64":
        work = tmp_path / "installer"
        work.mkdir()
        write_file_lists(destination / "BowlBound", work)
        install = (work / "install-files.nsh").read_text()
        uninstall = (work / "uninstall-files.nsh").read_text()
        assert install.count('File "/oname=roster.json"') == 2
        assert install.count('File "/oname=roster-sources.md"') == 2
        for name in roster_paths:
            assert name.replace("/", "\\") in uninstall


@pytest.mark.parametrize(
    "name",
    [
        "roster.json",
        "seasons/2007/cedar-valley/roster.json",
        "_internal/elsewhere/roster.json",
        "_internal/seasons/1900/private-team/roster.json",
        "_internal/seasons/2007/other-team/roster.json",
        "_internal/seasons/2007/cedar-valley/ROSTER.JSON",
        "_internal/seasons/2007/cedar-valley/private.pdf",
    ],
)
def test_native_roster_exception_does_not_allow_unselected_files(
    runtime: Path, tmp_path: Path, name: str
) -> None:
    bundle = fake_bundle(runtime, tmp_path / "bundle")
    put(bundle, name, "DO NOT SHIP")
    output = tmp_path / "output"
    output.mkdir()
    with pytest.raises(ReleaseError):
        native.archive_bundle(bundle, runtime, output, "macos-arm64")
    assert not list(output.iterdir())


@pytest.mark.parametrize("target", list(native.TARGETS))
def test_native_selected_roster_still_requires_unchanged_bytes(
    roster_runtime: Path, tmp_path: Path, target: str
) -> None:
    bundle = fake_bundle(roster_runtime, tmp_path / "bundle")
    executable = native.TARGETS[target][2]
    if executable != "Bowl-Bound":
        (bundle / "Bowl-Bound").rename(bundle / executable)
    put(bundle, "_internal/seasons/2007/cedar-valley/roster.json", "changed")
    output = tmp_path / "output"
    output.mkdir()
    with pytest.raises(ReleaseError, match="Native resource missing or changed"):
        native.archive_bundle(bundle, roster_runtime, output, target)
    assert not list(output.iterdir())
