"""Published-artifact validation uses downloaded bytes on every native target."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_post_release_smoke_downloads_without_building_or_publishing() -> None:
    text = (ROOT / ".github/workflows/post-release-smoke.yml").read_text()
    workflow = yaml.load(text, Loader=yaml.BaseLoader)
    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["on"]["workflow_dispatch"]["inputs"]["release_tag"]["required"] == "true"
    job = workflow["jobs"]["native"]
    assert job["strategy"]["fail-fast"] == "false"
    assert {(row["target"], row["kind"]) for row in job["strategy"]["matrix"]["include"]} == {
        ("macos-arm64", "portable"),
        ("macos-x86_64", "portable"),
        ("windows-x64", "portable"),
        ("windows-x64", "installer"),
        ("macos-arm64", "dmg"),
        ("macos-x86_64", "dmg"),
    }
    assert int(job["timeout-minutes"]) <= 30
    for step in job["steps"]:
        assert "continue-on-error" not in step
        if "uses" in step:
            assert re.fullmatch(r"actions/[a-z-]+@[a-f0-9]{40}", step["uses"])
    commands = "\n".join(step.get("run", "") for step in job["steps"])
    assert "gh release download" in commands and "gh api" in commands
    assert "--release-json" in commands and "--report" in commands
    assert "scripts.validate_install_artifact" in commands
    assert "playwright install chromium" in commands
    assert "build_standalone" not in commands and "release create" not in commands
    assert "pip install -e" not in commands
    assert "persist-credentials: false" in text
    uploads = [
        step for step in job["steps"] if step.get("uses", "").startswith("actions/upload-artifact@")
    ]
    assert len(uploads) == 1
    assert uploads[0]["if"] == "always() && (matrix.kind != 'dmg' || inputs.include_dmg)"
    assert "receipt.json" in uploads[0]["with"]["path"]
    assert "server.log" in uploads[0]["with"]["path"]
    assert "browser.png" in uploads[0]["with"]["path"]


def test_release_catalog_uses_exact_tag_checkout_independent_of_downloaded_app() -> None:
    workflow = yaml.load(
        (ROOT / ".github/workflows/post-release-smoke.yml").read_text(), Loader=yaml.BaseLoader
    )
    steps = workflow["jobs"]["native"]["steps"]
    checkouts = [step for step in steps if step.get("uses", "").startswith("actions/checkout@")]
    assert any(
        step.get("with", {}).get("ref") == "refs/tags/${{ inputs.release_tag }}"
        and step["with"].get("path") == "release-source"
        for step in checkouts
    )
    commands = "\n".join(step.get("run", "") for step in steps)
    assert "--catalog-manifest release-source/release/manifest.json" in commands


def test_dmg_checks_default_on_and_preserve_explicit_legacy_opt_out() -> None:
    text = (ROOT / ".github/workflows/post-release-smoke.yml").read_text()
    workflow = yaml.load(text, Loader=yaml.BaseLoader)
    assert workflow["on"]["workflow_dispatch"]["inputs"]["include_dmg"]["default"] == "true"
    steps = workflow["jobs"]["native"]["steps"]
    assert all("inputs.include_dmg" in step["if"] for step in steps)
    assert 'ASSET_NAME="BowlBound-$ARTIFACT_VERSION-$TARGET.dmg"' in text


def test_source_checks_run_fast_native_windows_terms_probe_in_parallel() -> None:
    workflow = yaml.load((ROOT / ".github/workflows/tests.yml").read_text(), Loader=yaml.BaseLoader)
    job = workflow["jobs"]["windows-terms-dialog"]
    assert job["runs-on"] == "windows-2025"
    assert job["env"]["PYTHON_VERSION"] == "3.12.10"
    assert "needs" not in job and int(job["timeout-minutes"]) <= 10
    commands = "\n".join(step.get("run", "") for step in job["steps"])
    assert "scripts.smoke_windows_terms --source-dialog WINDOWS-RUNTIME-TERMS.txt" in commands
    assert "build_standalone" not in commands and "pip install" not in commands
    uploads = [
        step for step in job["steps"] if step.get("uses", "").startswith("actions/upload-artifact@")
    ]
    assert len(uploads) == 1 and uploads[0]["if"] == "always()"
    assert "windows-terms-source.json" in uploads[0]["with"]["path"]


def test_published_native_matrix_uses_supported_intel_image_for_both_mac_assets() -> None:
    workflow = yaml.load(
        (ROOT / ".github/workflows/post-release-smoke.yml").read_text(), Loader=yaml.BaseLoader
    )
    rows = workflow["jobs"]["native"]["strategy"]["matrix"]["include"]
    assert {(row["target"], row["kind"]): row["os"] for row in rows} == {
        ("macos-arm64", "portable"): "macos-26",
        ("macos-arm64", "dmg"): "macos-26",
        ("macos-x86_64", "portable"): "macos-15-intel",
        ("macos-x86_64", "dmg"): "macos-15-intel",
        ("windows-x64", "portable"): "windows-2025",
        ("windows-x64", "installer"): "windows-2025",
    }
