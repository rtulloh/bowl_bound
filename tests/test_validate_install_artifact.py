"""Published install validation rejects wrong bytes before executing anything."""

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from unittest.mock import Mock
from zipfile import ZipFile, ZipInfo

import pytest

from scripts import smoke_standalone
from scripts import validate_install_artifact as validator

VERSION = "0.1.0-alpha.3"
TAG = "v" + VERSION


@pytest.fixture
def artifact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    monkeypatch.setattr(validator.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(validator.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(validator, "approved_catalog", lambda _: frozenset(validator.SAMPLES))
    archive = tmp_path / "app.zip"
    files = synthetic_inventory()
    contents = {name: b"synthetic" for name in files}
    contents["Bowl-Bound"] = b"synthetic"
    inventory = {
        "version": VERSION,
        "target": "macos-arm64",
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()},
    }
    contents["ARTIFACT-MANIFEST.json"] = json.dumps(inventory).encode()
    with ZipFile(archive, "w") as zipped:
        for name, data in contents.items():
            entry = ZipInfo("BowlBound/" + name)
            entry.external_attr = 0o100755 << 16
            zipped.writestr(entry, data)
    archive.with_suffix(".zip.sha256").write_text(
        hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name
    )
    metadata = tmp_path / "release.json"
    metadata.write_text(
        json.dumps(
            {
                "tag_name": TAG,
                "draft": False,
                "assets": [
                    {
                        "name": archive.name,
                        "size": archive.stat().st_size,
                        "digest": "sha256:" + hashlib.sha256(archive.read_bytes()).hexdigest(),
                    }
                ],
            }
        )
    )
    return archive, metadata, tmp_path / "out" / "receipt.json"


def synthetic_inventory() -> dict[str, str]:
    files = {
        f"seasons/{team}/{name}": "synthetic"
        for team in validator.SAMPLES
        for name in ("team.yaml", "offense.csv", "defense.csv", "special.csv")
    }
    files.update(
        {
            f"seasons/2007/provenance/{team.split('/')[1]}.csv": "synthetic"
            for team in validator.SAMPLES
        }
    )
    return files


def complete_smoke(
    *args: object,
    check_ui: Callable[[str], None],
    log_path: Path,
    expected_catalog: frozenset[str],
) -> None:
    """Simulate a native helper that completed its required live browser callback."""
    log_path.write_text("healthy server")
    check_ui("http://localhost")


def test_verified_download_launches_extracted_app_with_browser_and_persistent_log(
    artifact: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    archive, metadata, report = artifact
    browser_check = Mock()
    monkeypatch.setattr(validator, "check_browser", browser_check)
    launch = Mock(side_effect=complete_smoke)
    monkeypatch.setattr(validator, "smoke_executable", launch)
    assert validator.validate(archive, metadata, TAG, "macos-arm64", report) == 0
    executable, version, work = launch.call_args.args
    assert executable.name == "Bowl-Bound" and version == VERSION
    assert work != archive.parent and not work.exists()
    assert callable(launch.call_args.kwargs["check_ui"])
    assert launch.call_args.kwargs["log_path"] == report.parent / "server.log"
    receipt = json.loads(report.read_text())
    assert receipt["passed"] is True
    assert receipt["sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert receipt["artifact"] == archive.name
    assert receipt["target"] == "macos-arm64" and receipt["version"] == VERSION
    assert receipt["platform"] == "Darwin" and receipt["architecture"] == "arm64"
    assert receipt["manual_checks_pending"]
    assert receipt["browser"] == {
        "exact_catalog_selectors": True,
        "new_game": True,
        "generated_game": False,
        "cross_season_game": False,
    }
    browser_check.assert_called_once()


@pytest.mark.parametrize("mutation", ["tag", "draft", "size", "digest", "name", "missing-digest"])
def test_wrong_published_identity_never_launches(
    artifact: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    archive, metadata, report = artifact
    release = json.loads(metadata.read_text())
    if mutation == "tag":
        release["tag_name"] = "v9.0.0"
    elif mutation == "draft":
        release["draft"] = True
    elif mutation == "missing-digest":
        del release["assets"][0]["digest"]
    else:
        release["assets"][0][mutation] = 0 if mutation == "size" else "wrong"
    metadata.write_text(json.dumps(release))
    launch = Mock()
    monkeypatch.setattr(validator, "smoke_executable", launch)
    assert validator.validate(archive, metadata, TAG, "macos-arm64", report) == 1
    assert json.loads(report.read_text())["passed"] is False
    launch.assert_not_called()


@pytest.mark.parametrize(
    "target,tag,error",
    [
        ("macos-x86_64", TAG, "native"),
        ("macos-arm64", "invalid", "tag"),
    ],
)
def test_invalid_requested_target_or_tag_is_recorded(
    artifact: tuple[Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    tag: str,
    error: str,
) -> None:
    archive, metadata, report = artifact
    launch = Mock()
    monkeypatch.setattr(validator, "smoke_executable", launch)
    assert validator.validate(archive, metadata, tag, target, report) == 1
    assert error in json.loads(report.read_text())["error"].lower()
    launch.assert_not_called()


@pytest.mark.parametrize("field,value", [("version", "9.0.0-alpha.1"), ("target", "windows-x64")])
def test_zip_manifest_must_match_before_execution(
    artifact: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch, field: str, value: str
) -> None:
    archive, metadata, report = artifact
    monkeypatch.setattr(
        validator,
        "extract_verified",
        lambda *_: {"version": VERSION, "target": "macos-arm64", field: value},
    )
    launch = Mock()
    monkeypatch.setattr(validator, "smoke_executable", launch)
    assert validator.validate(archive, metadata, TAG, "macos-arm64", report) == 1
    assert field in json.loads(report.read_text())["error"].lower()
    launch.assert_not_called()


def test_bad_checksum_never_launches(
    artifact: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    archive, metadata, report = artifact
    archive.with_suffix(".zip.sha256").write_text("invalid")
    launch = Mock()
    monkeypatch.setattr(validator, "smoke_executable", launch)
    assert validator.validate(archive, metadata, TAG, "macos-arm64", report) == 1
    launch.assert_not_called()


def test_runtime_failure_is_persisted(
    artifact: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    archive, metadata, report = artifact
    monkeypatch.setattr(
        validator, "smoke_executable", Mock(side_effect=AssertionError("empty teams"))
    )
    assert validator.validate(archive, metadata, TAG, "macos-arm64", report) == 1
    assert "empty teams" in json.loads(report.read_text())["error"]


def test_installer_uses_same_ui_and_log_checks(
    artifact: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    _, metadata, report = artifact
    installer = metadata.parent / "BowlBoundSetup.exe"
    installer.write_bytes(b"synthetic installer")
    digest = hashlib.sha256(installer.read_bytes()).hexdigest()
    installer.with_suffix(".exe.sha256").write_text(digest + "  " + installer.name)
    metadata.write_text(
        json.dumps(
            {
                "tag_name": TAG,
                "draft": False,
                "assets": [
                    {
                        "name": installer.name,
                        "size": installer.stat().st_size,
                        "digest": "sha256:" + digest,
                    }
                ],
            }
        )
    )
    monkeypatch.setattr(validator.platform, "system", lambda: "Windows")
    monkeypatch.setattr(validator.platform, "machine", lambda: "AMD64")
    monkeypatch.setattr(validator, "check_browser", Mock())
    install = Mock(side_effect=complete_smoke)
    monkeypatch.setattr(validator, "smoke_installer", install)
    assert validator.validate(installer, metadata, TAG, "windows-x64", report) == 0
    assert install.call_args.args == (installer, VERSION)
    assert callable(install.call_args.kwargs["check_ui"])
    assert install.call_args.kwargs["log_path"] == report.parent / "server.log"


def test_child_process_environment_removes_source_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"):
        monkeypatch.setenv(key, "/source-checkout")
    monkeypatch.setenv("INSTALL_SMOKE_MARKER", "preserved")
    env = smoke_standalone.clean_environment()
    assert all(key not in env for key in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"))
    assert env["PYTHONNOUSERSITE"] == "1" and env["INSTALL_SMOKE_MARKER"] == "preserved"


@pytest.mark.parametrize(
    "failure",
    [
        None,
        "empty",
        "missing",
        "extra",
        "wrong-season",
        "wrong",
        "duplicate",
        "extra-season",
        "pageerror",
        "http-error",
        "game-start",
        "browser-error",
    ],
)
@pytest.mark.parametrize("generated", [False, True])
@pytest.mark.parametrize("picker_kind", ["legacy", "select", "combobox"])
def test_browser_verifies_rendered_samples_and_game_or_rejects_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str | None,
    generated: bool,
    picker_kind: str,
) -> None:
    """Exercise season-scoped DOM controls without launching a local browser."""
    import sys
    from types import ModuleType

    class BrowserError(Exception):
        pass

    expected_catalog = frozenset(validator.SAMPLES) | (
        {"2011/alpha", "2011/beta"} if generated else set()
    )
    seasons = sorted({team.split("/")[0] for team in expected_catalog})
    selected = dict(zip(("home", "away"), validator.SAMPLES, strict=True))
    current_season = {"home": "2007", "away": "2007"}
    opened = "home"
    starts: list[tuple[str, str]] = []
    page = Mock()

    def entries(side: str) -> list[str]:
        values = sorted(
            team
            for team in expected_catalog
            if picker_kind == "legacy" or team.startswith(current_season[side] + "/")
        )
        if failure == "empty":
            return []
        if failure == "missing":
            return values[:-1]
        if failure == "extra":
            return [*values, "2099/unexpected"]
        if failure == "wrong-season":
            foreign = next(
                (
                    team
                    for team in sorted(expected_catalog)
                    if not team.startswith(current_season[side] + "/")
                ),
                "2099/wrong-season",
            )
            return [foreign, *values[1:]]
        if failure == "wrong":
            return ["unexpected/team", *values[1:]]
        if failure == "duplicate":
            return [values[0]] * len(values)
        return values

    def choose(side: str, team: str) -> None:
        selected[side] = team
        if "/" in team:
            current_season[side] = team.split("/")[0]

    def option(side: str, team: str) -> Mock:
        control = Mock()
        control.inner_text.return_value = "Team " + team
        control.click.side_effect = lambda: choose(side, team)
        return control

    def options(side: str) -> Mock:
        control = Mock()
        control.count.side_effect = lambda: len(entries(side))
        control.nth.side_effect = lambda index: option(side, entries(side)[index])
        return control

    def listbox(side: str) -> Mock:
        control = Mock()

        def by_role(role: str, **kwargs: object) -> Mock:
            assert role == "option"
            if "name" in kwargs:
                name = str(kwargs["name"])
                team = next(team for team in entries(side) if "Team " + team == name)
                return option(side, team)
            return options(side)

        control.get_by_role.side_effect = by_role
        return control

    def by_id(identifier: str) -> Mock:
        nonlocal opened
        control = Mock()
        side = identifier.split("-")[0]
        if identifier.endswith("-season"):
            control.count.return_value = 0 if picker_kind == "legacy" else 1
            control.locator.return_value.evaluate_all.return_value = (
                seasons + ["2099"] if failure == "extra-season" else seasons
            )
            control.select_option.side_effect = lambda season: current_season.__setitem__(
                side, season
            )
        elif identifier.endswith("-select"):
            control.evaluate.return_value = "INPUT" if picker_kind == "combobox" else "SELECT"
            control.locator.return_value.evaluate_all.side_effect = lambda _: ["", *entries(side)]
            control.select_option.side_effect = lambda team: choose(side, team)
            control.get_attribute.side_effect = lambda _: selected[side]

            def open_picker() -> None:
                nonlocal opened
                opened = side

            control.click.side_effect = open_picker
        elif identifier == "start-game":

            def start() -> None:
                if failure == "game-start":
                    raise BrowserError("start game failed")
                assert selected["home"] != selected["away"]
                starts.append((selected["home"], selected["away"]))

            control.click.side_effect = start
        return control

    def by_role(role: str, **kwargs: object) -> Mock:
        assert role == "listbox"
        side = "home" if str(kwargs["name"]).startswith("Home") else "away"
        assert side == opened
        return listbox(side)

    page.get_by_test_id.side_effect = by_id
    page.get_by_role.side_effect = by_role
    if failure == "http-error":
        page.on.side_effect = lambda event, callback: (
            callback(Mock(status=500, url="http://localhost/api/teams"))
            if event == "response"
            else None
        )
    if failure == "pageerror":
        page.on.side_effect = lambda event, callback: (
            callback("UI failed") if event == "pageerror" else None
        )
    if failure == "browser-error":
        page.goto.side_effect = BrowserError("navigation failed")
    browser = Mock()
    browser.new_page.return_value = page
    context = Mock()
    context.chromium.launch.return_value = browser
    manager = Mock()
    manager.__enter__ = Mock(return_value=context)
    manager.__exit__ = Mock(return_value=False)
    module = ModuleType("playwright.sync_api")
    module.sync_playwright = Mock(return_value=manager)
    module.Error = BrowserError
    monkeypatch.setitem(sys.modules, "playwright.sync_api", module)
    # Legacy flat selects have no season control to expose an extra season.
    rejected = failure is not None and not (failure == "extra-season" and picker_kind == "legacy")
    if rejected:
        with pytest.raises((ValueError, RuntimeError)):
            validator.check_browser("http://localhost", tmp_path, expected_catalog)
    else:
        validator.check_browser("http://localhost", tmp_path, expected_catalog)
        assert starts[0] == tuple(validator.SAMPLES)
        if generated:
            assert ("2011/alpha", "2011/beta") in starts
            assert any(home.split("/")[0] != away.split("/")[0] for home, away in starts)
        else:
            assert len(starts) == 1
    browser.close.assert_called_once()
    page.screenshot.assert_called_once()


def test_executable_checks_browser_while_alive_and_isolates_both_child_launches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PYTHONPATH", "/source-checkout")
    (tmp_path / "ARTIFACT-MANIFEST.json").write_text(json.dumps({"files": synthetic_inventory()}))
    version_probe = Mock(return_value="Bowl Bound " + VERSION)
    process = Mock()
    process.poll.side_effect = [None, 0]
    process.wait.return_value = 0
    spawn = Mock(return_value=process)
    monkeypatch.setattr(smoke_standalone.subprocess, "check_output", version_probe)
    monkeypatch.setattr(smoke_standalone.subprocess, "Popen", spawn)
    monkeypatch.setattr(smoke_standalone, "request", Mock(return_value={"status": "healthy"}))
    monkeypatch.setattr(smoke_standalone, "exercise", Mock())
    ui = Mock(side_effect=lambda _: process.send_signal.assert_not_called())
    persistent_log = tmp_path / "persisted.log"
    smoke_standalone.smoke_executable(
        tmp_path / "app", VERSION, tmp_path, check_ui=ui, log_path=persistent_log
    )
    ui.assert_called_once()
    process.send_signal.assert_called_once()
    assert persistent_log.exists()
    assert "PYTHONPATH" not in version_probe.call_args.kwargs["env"]
    assert "PYTHONPATH" not in spawn.call_args.kwargs["env"]


@pytest.mark.parametrize("evidence", ["receipt.json", "server.log", "browser.png"])
def test_existing_evidence_is_preserved(artifact: tuple[Path, Path, Path], evidence: str) -> None:
    archive, metadata, report = artifact
    report.parent.mkdir()
    existing = report.parent / evidence
    existing.write_text("previous evidence")
    with pytest.raises(ValueError, match="fresh"):
        validator.validate(archive, metadata, TAG, "macos-arm64", report)
    assert existing.read_text() == "previous evidence"


def test_missing_runtime_log_cannot_pass(
    artifact: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    archive, metadata, report = artifact
    monkeypatch.setattr(validator, "smoke_executable", Mock())
    assert validator.validate(archive, metadata, TAG, "macos-arm64", report) == 1
    assert "log" in json.loads(report.read_text())["error"].lower()


@pytest.mark.parametrize("name", ["server.log", "browser.png"])
def test_receipt_cannot_overwrite_reserved_evidence(
    artifact: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    archive, metadata, report = artifact
    launch = Mock()
    monkeypatch.setattr(validator, "smoke_executable", launch)
    with pytest.raises(ValueError, match="reserved"):
        validator.validate(archive, metadata, TAG, "macos-arm64", report.parent / name)
    launch.assert_not_called()


def test_runtime_success_without_browser_callback_is_rejected(
    artifact: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    archive, metadata, report = artifact
    monkeypatch.setattr(
        validator,
        "smoke_executable",
        Mock(side_effect=lambda *args, **kwargs: kwargs["log_path"].write_text("healthy server")),
    )
    assert validator.validate(archive, metadata, TAG, "macos-arm64", report) == 1
    receipt = json.loads(report.read_text())
    assert not receipt["passed"] and "browser" in receipt["error"].lower()


def test_approved_catalog_is_independent_of_observed_archive_or_api(tmp_path: Path) -> None:
    inventory = {
        f"seasons/2011/{team}/{name}": "synthetic"
        for team in ("alpha", "beta", "gamma")
        for name in ("team.yaml", "offense.csv", "defense.csv", "special.csv")
    }
    inventory.update(
        {f"seasons/2011/provenance/{team}.csv": "synthetic" for team in ("alpha", "beta", "gamma")}
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"sample_sha256": {}, "generated_sha256": inventory}))
    assert validator.approved_catalog(manifest) == frozenset(
        {"2011/alpha", "2011/beta", "2011/gamma"}
    )


def test_release_source_catalog_contains_exact_approved_173_teams() -> None:
    manifest = Path(__file__).resolve().parents[1] / "release/manifest.json"
    expected = validator.approved_catalog(manifest)
    samples = set(validator.SAMPLES)
    assert len(expected) == 173
    assert samples.issubset(expected)
    generated = expected - samples
    assert len({team for team in generated if team.startswith("2002/")}) == 55
    assert len({team for team in generated if team.startswith("2007/")}) == 116
    assert all(team.startswith(("2002/", "2007/")) for team in expected)


def test_incomplete_archive_catalog_is_rejected_against_approved_catalog(
    artifact: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    archive, metadata, report = artifact
    monkeypatch.setattr(
        validator, "approved_catalog", lambda _: frozenset(validator.SAMPLES) | {"2011/missing"}
    )
    launch = Mock()
    monkeypatch.setattr(validator, "smoke_executable", launch)
    assert validator.validate(archive, metadata, TAG, "macos-arm64", report) == 1
    assert "catalog" in json.loads(report.read_text())["error"].lower()
    launch.assert_not_called()
