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
