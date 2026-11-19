"""Mac installer composition uses synthetic portable bundles."""

import plistlib
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from scripts import macos_dmg
from scripts.release_package import ReleaseError


def test_app_preserves_payload_and_finder_opens_terminal(tmp_path: Path) -> None:
    payload = tmp_path / "portable"
    payload.mkdir()
    (payload / "Bowl-Bound").write_text("synthetic executable")
    (payload / "start.sh").write_text("synthetic launcher")
    app = macos_dmg.assemble_app(payload, tmp_path / "Bowl Bound.app", "1.1.1")
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    assert info["CFBundleShortVersionString"] == "1.1.1"
    assert info["CFBundleExecutable"] == "launch"
    launch = app / "Contents/MacOS/launch"
    command = app / "Contents/Resources/start.command"
    assert launch.stat().st_mode & 0o111
    assert command.stat().st_mode & 0o111
    assert "/usr/bin/open -a Terminal" in launch.read_text()
    assert "start.command" in launch.read_text()
    assert 'exec "$APP_DIR/../MacOS/BowlBound/start.sh" "$@"' in command.read_text()
    for script in (launch, command):
        subprocess.run(["/bin/bash", "-n", str(script)], check=True)
    assert (app / "Contents/MacOS/BowlBound/Bowl-Bound").read_text() == "synthetic executable"
    assert "xattr" not in launch.read_text() + command.read_text()


def test_app_rejects_symlink_payload_and_existing_destination(tmp_path: Path) -> None:
    payload = tmp_path / "portable"
    payload.mkdir()
    (payload / "escape").symlink_to(tmp_path)
    with pytest.raises(ReleaseError, match="symlink"):
        macos_dmg.assemble_app(payload, tmp_path / "Bowl Bound.app", "1.1.1")
    assert not (tmp_path / "Bowl Bound.app").exists()
    (payload / "escape").unlink()
    destination = tmp_path / "exists.app"
    destination.mkdir()
    with pytest.raises(ReleaseError, match="exist"):
        macos_dmg.assemble_app(payload, destination, "1.1.1")


def test_workflow_builds_smokes_and_uploads_both_mac_images() -> None:
    text = Path(".github/workflows/build.yml").read_text()
    assert "target: macos-arm64" in text
    assert "target: macos-x86_64" in text
    assert "scripts.macos_dmg" in text and "--smoke" in text
    assert "bowl-bound-artifacts/*.dmg" in text
    assert "bowl-bound-artifacts/*.receipt.json" in text


def test_finder_smoke_launches_app_checks_owner_and_sends_ctrl_c(tmp_path: Path) -> None:
    app = tmp_path / "Bowl Bound.app"
    executable = app / "Contents/MacOS/BowlBound/Bowl-Bound"
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
        (destination / "BowlBound").mkdir(parents=True)
        return {"version": "1.1.1", "target": "macos-arm64"}

    def fail(command: list[str], **_kwargs: object) -> None:
        Path(command[-1]).write_bytes(b"partial image")
        raise subprocess.CalledProcessError(1, command)

    with (
        patch.object(macos_dmg, "extract_verified", side_effect=extract),
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
    executable = app / "Contents/MacOS/BowlBound/Bowl-Bound"
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
