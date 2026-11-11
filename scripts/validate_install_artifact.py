"""Validate downloaded release bytes and exercise their native app and rendered UI."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import BadZipFile

from .build_standalone import TARGETS, check_target
from .smoke_standalone import catalog_from_inventory, extract_verified, smoke_executable
from .windows_installer import smoke_installer

SAMPLES = ["2007/cedar-valley", "2007/harbor-tech"]
DEFAULT_CATALOG_MANIFEST = Path(__file__).resolve().parents[1] / "release/manifest.json"


def approved_catalog(manifest_path: Path) -> frozenset[str]:
    """Read expected public teams from the independently checked-out release source."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = {**manifest["sample_sha256"], **manifest["generated_sha256"]}
    return catalog_from_inventory(files)


def check_browser(base: str, output: Path, expected_catalog: frozenset[str]) -> None:
    """Convert browser-tool failures into reportable validation failures."""
    from playwright.sync_api import Error as BrowserError

    try:
        _check_browser(base, output, expected_catalog)
    except BrowserError as error:
        raise RuntimeError(f"Packaged browser verification failed: {error}") from error


def _check_browser(base: str, output: Path, expected_catalog: frozenset[str]) -> None:
    """Require actual bundled team selectors and a successfully created UI game."""
    from playwright.sync_api import sync_playwright

    errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        try:
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on(
                "requestfailed", lambda request: errors.append(f"Failed request: {request.url}")
            )
            page.on(
                "response",
                lambda response: (
                    errors.append(f"HTTP {response.status}: {response.url}")
                    if response.url.startswith(base) and response.status >= 400
                    else None
                ),
            )
            page.goto(base)
            for side in ("home", "away"):
                selector = page.get_by_test_id(side + "-select")
                selector.wait_for()
                options = selector.locator("option").evaluate_all(
                    "(items) => items.map(item => item.value)"
                )
                if sorted(options) != sorted(expected_catalog):
                    raise ValueError(
                        f"Packaged {side} selector differs from the approved release catalog"
                    )
                selector.select_option(SAMPLES[0 if side == "home" else 1])
            page.get_by_label("Control mode").select_option("manual")
            page.get_by_test_id("start-game").click()
            page.get_by_test_id("opening-screen").wait_for()
            generated = sorted(expected_catalog - set(SAMPLES))
            if generated:
                if len(generated) < 2:
                    raise ValueError("Generated browser validation requires two distinct teams")
                page.goto(base)
                page.get_by_label("Control mode").select_option("manual")
                page.get_by_test_id("home-select").select_option(generated[0])
                page.get_by_test_id("away-select").select_option(generated[1])
                page.get_by_test_id("start-game").click()
                page.get_by_test_id("opening-screen").wait_for()
            if errors:
                raise RuntimeError(f"Packaged UI errors: {errors}")
        finally:
            try:
                page.screenshot(path=str(output / "browser.png"), full_page=True)
            finally:
                browser.close()


def verify_identity(artifact: Path, release_json: Path, tag: str, digest: str) -> None:
    """Require published metadata and a checksum sidecar for the exact local bytes."""
    release = json.loads(release_json.read_text(encoding="utf-8"))
    if release["tag_name"] != tag or release["draft"] is not False:
        raise ValueError("Release metadata must match the published non-draft tag")
    matches = [asset for asset in release["assets"] if asset["name"] == artifact.name]
    if len(matches) != 1:
        raise ValueError("Release must identify exactly one matching artifact")
    asset = matches[0]
    if asset["size"] != artifact.stat().st_size or asset.get("digest") != "sha256:" + digest:
        raise ValueError("Published artifact size or SHA-256 digest mismatch")
    checksum = artifact.with_suffix(artifact.suffix + ".sha256").read_text(encoding="utf-8").split()
    if checksum != [digest, artifact.name]:
        raise ValueError("Downloaded artifact checksum mismatch")


def validate(
    artifact: Path,
    release_json: Path,
    tag: str,
    target: str,
    report: Path,
    *,
    catalog_manifest: Path = DEFAULT_CATALOG_MANIFEST,
) -> int:
    """Write success/failure evidence; never launch mismatched or unverified bytes."""
    if report.name.casefold() in {"server.log", "browser.png"}:
        raise ValueError("Report filename is reserved for logs or screenshots")
    evidence = (report, report.parent / "server.log", report.parent / "browser.png")
    if any(path.exists() or path.is_symlink() for path in evidence):
        raise ValueError(
            "Choose fresh report, log and screenshot paths; existing evidence is preserved"
        )
    report.parent.mkdir(parents=True, exist_ok=True)
    receipt: dict[str, object] = {
        "passed": False,
        "artifact": artifact.name,
        "tag": tag,
        "target": target,
        "platform": platform.system(),
        "architecture": platform.machine(),
        "manual_checks_pending": [
            "Fresh-download first-launch security, signing and quarantine acceptance"
        ],
    }
    try:
        if not re.fullmatch(r"v\d+\.\d+\.\d+(?:-alpha\.\d+)?", tag):
            raise ValueError("Expected a version tag such as v0.1.0-alpha.4")
        version = tag[1:]
        receipt["version"] = version
        executable_name = check_target(target, platform.system(), platform.machine())
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        receipt["sha256"] = digest
        verify_identity(artifact, release_json, tag, digest)
        expected_catalog = approved_catalog(catalog_manifest)
        receipt["expected_team_ids"] = sorted(expected_catalog)
        receipt["catalog_manifest_sha256"] = hashlib.sha256(
            catalog_manifest.read_bytes()
        ).hexdigest()
        if artifact.suffix.lower() not in {".zip", ".exe"}:
            raise ValueError("Expected a standalone ZIP or Windows installer EXE")
        if artifact.suffix.lower() == ".exe" and target != "windows-x64":
            raise ValueError("Installer EXE requires the Windows native target")

        def browser_check(base: str) -> None:
            check_browser(base, report.parent, expected_catalog)
            receipt["browser"] = {
                "exact_catalog_selectors": True,
                "new_game": True,
                "generated_game": bool(expected_catalog - set(SAMPLES)),
            }

        options = {
            "check_ui": browser_check,
            "log_path": report.parent / "server.log",
            "expected_catalog": expected_catalog,
        }
        if artifact.suffix.lower() == ".exe":
            smoke_installer(artifact.resolve(), version, **options)
            receipt["launch_method"] = "Installed Windows application; uninstall verified"
        else:
            with TemporaryDirectory(prefix="bb-published-smoke-") as directory:
                work = Path(directory)
                manifest = extract_verified(artifact, work)
                if manifest["version"] != version:
                    raise ValueError("Archive manifest version differs from requested tag")
                if manifest["target"] != target:
                    raise ValueError("Archive manifest target differs from requested target")
                if catalog_from_inventory(manifest["files"]) != expected_catalog:
                    raise ValueError("Archive catalog differs from approved release catalog")
                smoke_executable(work / "BowlBound" / executable_name, version, work, **options)
            receipt["launch_method"] = "Verified extracted standalone executable"
        log_path = report.parent / "server.log"
        if not log_path.is_file():
            raise RuntimeError("Packaged server log is missing")
        errors = [
            line
            for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            if re.search(r"Traceback|PydanticUserError|\bERROR\b", line)
        ]
        if errors:
            raise RuntimeError("Packaged server emitted error logs: " + "\n".join(errors))
        if "browser" not in receipt:
            raise RuntimeError("Required browser verification callback did not complete")
        receipt["passed"] = True
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        RuntimeError,
        AssertionError,
        ImportError,
        subprocess.SubprocessError,
        BadZipFile,
    ) as error:
        receipt["error"] = f"{type(error).__name__}: {error}"
    report.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return 0 if receipt["passed"] else 1


def main() -> int:
    """Run only against explicitly selected already-downloaded release artifacts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--release-json", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--target", choices=TARGETS, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--catalog-manifest",
        type=Path,
        default=DEFAULT_CATALOG_MANIFEST,
    )
    args = parser.parse_args()
    return validate(
        args.artifact,
        args.release_json,
        args.tag,
        args.target,
        args.report,
        catalog_manifest=args.catalog_manifest,
    )


if __name__ == "__main__":
    raise SystemExit(main())
