"""Mac installer composition uses synthetic portable bundles."""

import json
import plistlib
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from scripts import macos_dmg
from scripts.release_package import ReleaseError


@pytest.mark.parametrize(
    ("target", "architecture"), [("macos-arm64", "arm64"), ("macos-x86_64", "x86_64")]
)
def test_script_app_selects_its_payload_architecture(
    tmp_path: Path, target: str, architecture: str
) -> None:
    payload = tmp_path / "portable"
    (payload / "_internal").mkdir(parents=True)
    (payload / "Bowl-Bound").write_text("synthetic executable")
    app = macos_dmg.assemble_app(payload, tmp_path / "Bowl Bound.app", "1.1.2", target=target)
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    assert info["LSArchitecturePriority"] == [architecture]
    assert "LSRequiresNativeExecution" not in info


def test_script_app_rejects_unsupported_target_before_copy(tmp_path: Path) -> None:
    payload = tmp_path / "portable"
    payload.mkdir()
    app = tmp_path / "Bowl Bound.app"
    with pytest.raises(ReleaseError, match="macOS target"):
        macos_dmg.assemble_app(payload, app, "1.1.2", target="windows-x64")
    assert not app.exists()


def test_app_rejects_symlink_payload_and_existing_destination(tmp_path: Path) -> None:
    payload = tmp_path / "portable"
    payload.mkdir()
    (payload / "escape").symlink_to(tmp_path)
    with pytest.raises(ReleaseError, match="symlink"):
        macos_dmg.assemble_app(payload, tmp_path / "Bowl Bound.app", "1.1.1", target="macos-arm64")
    assert not (tmp_path / "Bowl Bound.app").exists()
    (payload / "escape").unlink()
    destination = tmp_path / "exists.app"
    destination.mkdir()
    with pytest.raises(ReleaseError, match="exist"):
        macos_dmg.assemble_app(payload, destination, "1.1.1", target="macos-arm64")


def test_workflow_builds_smokes_and_uploads_both_mac_images() -> None:
    text = Path(".github/workflows/build.yml").read_text()
    assert "target: macos-arm64" in text
    assert "target: macos-x86_64" in text
    assert "scripts.macos_dmg" in text and "--smoke" in text
    assert "bowl-bound-artifacts/*.dmg" in text
    assert "bowl-bound-artifacts/*.receipt.json" in text


def test_finder_smoke_launches_app_checks_owner_and_sends_ctrl_c(tmp_path: Path) -> None:
    app = tmp_path / "Bowl Bound.app"
    executable = app / "Contents/MacOS/Bowl-Bound"
    executable.parent.mkdir(parents=True)
    executable.write_text("synthetic executable")
    with (
        patch.object(macos_dmg.socket, "socket"),
        patch.object(macos_dmg.subprocess, "run", return_value=Mock(stdout="123\n")) as run,
        patch.object(macos_dmg.subprocess, "check_output", return_value="n" + str(executable)),
        patch.object(
            macos_dmg, "request", side_effect=[{"status": "healthy"}, {"version": "1.1.1"}]
        ),
        patch.object(macos_dmg.os, "kill", side_effect=[None, ProcessLookupError]) as kill,
    ):
        macos_dmg.smoke_finder_app(app, "1.1.1")
    assert run.call_args_list[0].args[0] == ["/usr/bin/open", "-n", str(app)]
    assert kill.call_args_list[0].args == (123, macos_dmg.signal.SIGINT)


def test_finder_smoke_never_stops_someone_elses_listener(tmp_path: Path) -> None:
    with (
        patch.object(macos_dmg.socket, "socket"),
        patch.object(macos_dmg.subprocess, "run", return_value=Mock(stdout="456\n")),
        patch.object(macos_dmg.subprocess, "check_output", return_value="/other/server"),
        patch.object(macos_dmg.os, "kill") as kill,
        pytest.raises(ReleaseError, match="another executable"),
    ):
        macos_dmg.smoke_finder_app(tmp_path / "Bowl Bound.app", "1.1.1")
    kill.assert_not_called()


def test_existing_receipt_is_not_overwritten(tmp_path: Path) -> None:
    archive = tmp_path / "input.zip"
    receipt = archive.with_suffix(".dmg.receipt.json")
    receipt.write_text("prior evidence")
    with pytest.raises(ReleaseError, match="receipt"):
        macos_dmg.build_dmg(archive)
    assert receipt.read_text() == "prior evidence"


def test_failed_image_creation_leaves_final_path_free_for_retry(tmp_path: Path) -> None:
    archive = tmp_path / "input.zip"
    archive.write_bytes(b"synthetic archive")

    def extract(_archive: Path, destination: Path) -> dict[str, str]:
        payload = destination / "BowlBound"
        (payload / "_internal").mkdir(parents=True)
        (payload / "Bowl-Bound").write_text("synthetic executable")
        return {"version": "1.1.1", "target": "macos-arm64"}

    def fail(command: list[str], **_kwargs: object) -> None:
        Path(command[-1]).write_bytes(b"partial image")
        raise subprocess.CalledProcessError(1, command)

    with (
        patch.object(macos_dmg, "extract_verified", side_effect=extract),
        patch.object(macos_dmg, "seal_app"),
        patch.object(macos_dmg.subprocess, "run", side_effect=fail) as run,
    ):
        for _ in range(2):
            with pytest.raises(subprocess.CalledProcessError):
                macos_dmg.build_dmg(archive)
            assert not archive.with_suffix(".dmg").exists()
            assert not archive.with_suffix(".dmg.sha256").exists()
        assert run.call_count == 2


def test_finder_listener_identity_accepts_canonical_alias_paths(tmp_path: Path) -> None:
    real = tmp_path / "physical"
    real.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    app = alias / "Bowl Bound.app"
    executable = app / "Contents/Resources/BowlBound/Bowl-Bound"
    executable.parent.mkdir(parents=True)
    executable.write_text("synthetic executable")
    with (
        patch.object(macos_dmg.socket, "socket"),
        patch.object(macos_dmg.subprocess, "run", return_value=Mock(stdout="123\n")),
        patch.object(
            macos_dmg.subprocess, "check_output", return_value="n" + str(executable.resolve())
        ),
        patch.object(
            macos_dmg, "request", side_effect=[{"status": "healthy"}, {"version": "1.1.1"}]
        ),
        patch.object(macos_dmg.os, "kill", side_effect=[None, ProcessLookupError]) as kill,
    ):
        macos_dmg.smoke_finder_app(app, "1.1.1")
    assert kill.call_args_list[0].args == (123, macos_dmg.signal.SIGINT)


def test_failed_finder_smoke_preserves_app_for_potentially_running_server(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    copied_apps: list[Path] = []

    def mount(command: list[str], **_kwargs: object) -> None:
        if command[1] == "attach":
            mounted = Path(command[command.index("-mountpoint") + 1])
            payload = mounted / "Bowl Bound.app/Contents/Resources/BowlBound"
            payload.mkdir(parents=True)
            (payload / "ARTIFACT-MANIFEST.json").write_text(
                json.dumps({"version": "1.1.1", "target": "macos-arm64"})
            )
            (payload / "Bowl-Bound").write_text("synthetic executable")

    def fail(app: Path, _version: str) -> None:
        copied_apps.append(app)
        raise ReleaseError("ownership was not established")

    with (
        patch.object(macos_dmg.subprocess, "run", side_effect=mount),
        patch.object(macos_dmg, "smoke_finder_app", side_effect=fail),
        pytest.raises(ReleaseError, match="ownership"),
    ):
        macos_dmg.smoke_dmg(tmp_path / "synthetic.dmg", "1.1.1", "macos-arm64")
    assert len(copied_apps) == 1
    assert (copied_apps[0] / "Contents/Resources/BowlBound/Bowl-Bound").is_file()
    assert str(copied_apps[0]) in capsys.readouterr().err
    import shutil

    shutil.rmtree(copied_apps[0].parents[1])


def test_completed_app_is_sealed_and_verified_fail_closed(tmp_path: Path) -> None:
    app = tmp_path / "Bowl Bound.app"
    with patch.object(macos_dmg.subprocess, "run") as run:
        macos_dmg.seal_app(app)
    assert [call.args[0] for call in run.call_args_list] == [
        ["codesign", "--force", "--sign", "-", "--timestamp=none", str(app)],
        ["codesign", "--verify", "--deep", "--strict", str(app)],
    ]
    assert all(call.kwargs["check"] is True for call in run.call_args_list)
    with (
        patch.object(
            macos_dmg.subprocess,
            "run",
            side_effect=[None, subprocess.CalledProcessError(1, "codesign")],
        ),
        pytest.raises(subprocess.CalledProcessError),
    ):
        macos_dmg.seal_app(app)


def test_data_payload_lives_in_resources_for_completed_bundle_signing(tmp_path: Path) -> None:
    payload = tmp_path / "portable"
    internal = payload / "_internal"
    internal.mkdir(parents=True)
    (internal / "WINDOWS-RUNTIME-TERMS.txt").write_text("synthetic terms")
    (payload / "Bowl-Bound").write_text("synthetic executable")
    app = macos_dmg.assemble_app(
        payload, tmp_path / "Bowl Bound.app", "1.1.2", target="macos-arm64"
    )
    assert sorted(p.name for p in (app / "Contents/MacOS").iterdir()) == ["Bowl-Bound"]
    assert (
        app / "Contents/Resources/BowlBound/_internal/WINDOWS-RUNTIME-TERMS.txt"
    ).read_text() == "synthetic terms"


def test_app_finder_starts_portable_executable_with_bundled_frameworks(tmp_path: Path) -> None:
    payload = tmp_path / "portable"
    (payload / "_internal").mkdir(parents=True)
    executable = payload / "Bowl-Bound"
    executable.write_bytes(b"synthetic portable executable")
    executable.chmod(0o755)
    (payload / "_internal" / "module").write_bytes(b"synthetic module")
    app = macos_dmg.assemble_app(
        payload, tmp_path / "Bowl Bound.app", "1.1.2", target="macos-arm64"
    )
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    assert info["CFBundleExecutable"] == "Bowl-Bound"
    assert "LSUIElement" not in info
    assert (app / "Contents/MacOS/Bowl-Bound").read_bytes() == executable.read_bytes()
    assert (app / "Contents/MacOS/Bowl-Bound").stat().st_mode & 0o111
    assert not (app / "Contents/Resources/start.command").exists()
    assert (app / "Contents/Frameworks").readlink() == Path("Resources/BowlBound/_internal")
    assert (app / "Contents/Frameworks/module").read_bytes() == b"synthetic module"


def test_smoke_copy_preserves_bundle_frameworks_link(tmp_path: Path) -> None:
    def mount(command: list[str], **_kwargs: object) -> None:
        if command[1] == "attach":
            mounted = Path(command[command.index("-mountpoint") + 1])
            payload = tmp_path / "portable"
            (payload / "_internal").mkdir(parents=True)
            (payload / "Bowl-Bound").write_bytes(b"synthetic executable")
            (payload / "ARTIFACT-MANIFEST.json").write_text(
                json.dumps({"version": "1.1.2", "target": "macos-arm64"})
            )
            macos_dmg.assemble_app(
                payload, mounted / "Bowl Bound.app", "1.1.2", target="macos-arm64"
            )

    def smoke(app: Path, _version: str) -> None:
        assert (app / "Contents/Frameworks").readlink() == Path("Resources/BowlBound/_internal")
        assert (app / "Contents/Frameworks").resolve().is_dir()

    with (
        patch.object(macos_dmg.subprocess, "run", side_effect=mount),
        patch.object(macos_dmg, "smoke_finder_app", side_effect=smoke),
        patch.object(macos_dmg, "smoke_executable") as direct,
    ):
        macos_dmg.smoke_dmg(tmp_path / "synthetic.dmg", "1.1.2", "macos-arm64")
    assert direct.call_args.args[0].as_posix().endswith("/Contents/MacOS/Bowl-Bound")
    assert (
        direct.call_args.kwargs["payload_root"].as_posix().endswith("/Contents/Resources/BowlBound")
    )
