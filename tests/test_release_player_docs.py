"""Player artifacts carry only reviewed public guides, not developer notes."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYER_FILES = {
    "README.md",
    "RELEASE_NOTES.md",
    "docs/README.md",
    "docs/installation.md",
    "docs/playing.md",
    "docs/startup.md",
    "docs/troubleshooting.md",
    "docs/reporting-bugs.md",
    "docs/versioning.md",
    "docs/THIRD_PARTY_NOTICES.md",
    "docs/importing-teams.md",
    "docs/python-setup.md",
}


def test_player_documents_are_selected_without_developer_material() -> None:
    manifest = json.loads((ROOT / "release/manifest.json").read_text(encoding="utf-8"))
    assert PLAYER_FILES <= set(manifest["runtime"])
    assert not any(
        "dev-notes" in name or name.endswith("opencode.json") for name in manifest["runtime"]
    )
    for name in PLAYER_FILES:
        text = (ROOT / name).read_text(encoding="utf-8")
        assert not re.search(r"/Users/|/private/var/|DEV-\d+|FLOW-\d+|ses_[a-zA-Z0-9]", text), name
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            if "://" in target or target.startswith(("mailto:", "#")):
                continue
            resolved = (ROOT / name).parent.joinpath(target.split("#", 1)[0]).resolve()
            assert resolved.is_file(), (name, target)
            assert resolved.relative_to(ROOT).as_posix() in manifest["runtime"], (name, target)


def test_bug_report_contact_and_download_security_guidance() -> None:
    bug_guide = (ROOT / "docs/reporting-bugs.md").read_text(encoding="utf-8")
    assert "bowlboundsupport@gmail.com" in bug_guide
    assert all(
        word in bug_guide.lower()
        for word in ("version", "description", "logs", "private", "expected")
    )
    installation = (ROOT / "docs/installation.md").read_text(encoding="utf-8")
    assert "BowlBound.exe" in installation
    assert "Unblock" in installation and "SmartScreen" in installation
    assert "xattr -dr com.apple.quarantine" in installation
    assert "macOS-only" in installation


def test_player_docs_present_browser_before_offline_installation() -> None:
    """The hosted browser edition is the recommended way to play."""
    browser = "https://rtulloh.github.io/bowl_bound/"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    player_guide = (ROOT / "docs/README.md").read_text(encoding="utf-8")
    installation = (ROOT / "docs/installation.md").read_text(encoding="utf-8")
    playing = (ROOT / "docs/playing.md").read_text(encoding="utf-8")
    startup = (ROOT / "docs/startup.md").read_text(encoding="utf-8")

    for text in (readme, player_guide, installation, playing, startup):
        assert browser in text
        assert "recommended" in text.lower()

    assert readme.index(browser) < readme.index("## Optional offline downloads")
    assert installation.index(browser) < installation.index("## Standalone downloads")
    assert playing.index(browser) < playing.index("local game](startup.md)")


def test_player_documents_state_manifest_catalog_counts() -> None:
    """Player catalog totals must match the pinned release manifest."""
    manifest = json.loads((ROOT / "release/manifest.json").read_text(encoding="utf-8"))

    def teams(section: str) -> set[str]:
        return {
            "/".join(name.split("/")[1:3])
            for name in manifest[section]
            if name.startswith("seasons/") and name.endswith("/team.yaml")
        }

    generated = teams("generated_sha256")
    playable = generated | teams("sample_sha256")
    assert (len(generated), len(playable)) == (179, 181)

    for name in ("RELEASE_NOTES.md", "docs/generated-charts.md", "docs/installation.md"):
        text = " ".join((ROOT / name).read_text(encoding="utf-8").split())
        assert f"{len(generated)} generated teams" in text, name
        assert f"{len(playable)} playable teams" in text, name
