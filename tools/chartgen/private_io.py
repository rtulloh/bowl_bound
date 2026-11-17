"""Shared privacy boundary for historical source, generated charts and reports."""

from pathlib import Path


def private_destination(path: Path) -> Path:
    """Validate unresolved parents before resolving traversal; never follow links."""
    absolute = path.absolute()
    if any(parent.is_symlink() for parent in (absolute, *absolute.parents)):
        raise ValueError("private output paths may not contain a symlink")
    resolved = absolute.resolve()
    if "private-data" not in resolved.parts:
        raise ValueError("historical evidence and outputs require a private-data path")
    return resolved
