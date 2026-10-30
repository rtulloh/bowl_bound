"""Safe CLI boundary for the development-only PDF inspection pipeline."""

import argparse
import json
import os
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

from .inspection import ImportInspectionError, inspect_document


def export_document(path: Path) -> list:
    """Load the export pipeline lazily so inspection never needs it."""
    from .export import export_document as run_export

    return run_export(path)


def _source_path(path: Path) -> Path:
    if path.is_dir():
        candidates = sorted(
            entry
            for entry in path.iterdir()
            if entry.suffix.lower() == ".pdf" and not entry.name.startswith(".")
        )
        if any(entry.is_symlink() for entry in candidates):
            raise ValueError("Refusing a symlinked PDF in the input directory")
        candidates = [entry for entry in candidates if entry.is_file()]
        if len(candidates) != 1:
            raise ValueError(
                "Directory input currently requires exactly one PDF; "
                "multi-file batch import is not yet supported"
            )
        return candidates[0]
    if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".pdf":
        raise ValueError("Input must be an existing, non-symlink PDF or a directory with one PDF")
    return path


def _refuse_symlinked_parents(output: Path) -> None:
    absolute = Path(os.path.abspath(output))
    for parent in absolute.parents:
        if parent.is_symlink() and parent != Path(parent.anchor):
            raise ValueError("Refusing an output path that passes through a symlinked directory")


def _validate_output(source: Path, output: Path, force: bool) -> None:
    try:
        same_path = output.resolve() == source.resolve()
        same_file = output.exists() and os.path.samefile(source, output)
    except (OSError, RuntimeError) as error:
        raise ValueError("Output path cannot be resolved safely") from error
    if same_path or same_file:
        raise ValueError("Output must not replace the source PDF")
    if output.is_symlink():
        raise ValueError("Refusing a symlink output path")
    _refuse_symlinked_parents(output)
    if output.exists() and not output.is_file():
        raise ValueError("Output must be a file, not a directory")
    if output.exists() and not force:
        raise ValueError("Output exists; pass --force to explicitly replace it")


def _write_report(source: Path, output: Path, rendered: str | bytes, force: bool) -> None:
    """Write a private report atomically; never modify any pre-existing inode in place."""
    _validate_output(source, output, force)  # re-check immediately before writing
    created: list[Path] = []
    parent = output.parent
    missing = [p for p in (parent, *parent.parents) if not p.exists()]
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
        created.append(directory)
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(prefix=".inspection-", suffix=".tmp", dir=parent)
        temporary = Path(name)
        data = rendered.encode("utf-8") if isinstance(rendered, str) else rendered
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        if not force:
            _validate_output(source, output, False)
            os.link(temporary, output)  # fails if the name appeared after the check
            temporary.unlink()
        else:
            os.replace(temporary, output)
        temporary = None
    except BaseException:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        for directory in reversed(created):
            try:
                directory.rmdir()
            except OSError:
                pass
        raise


def _verify_teams(teams: list) -> None:
    """Round-trip every team through the strict file codec so nothing unreadable is written."""
    from bowl_bound.team_csv import provenance_to_csv, team_from_files, team_to_files

    for team in teams:
        decoded = team_from_files(
            team_to_files(team.chart, team.metadata), provenance_to_csv(team.chart, team.metadata)
        )
        if decoded != (team.chart, team.metadata):
            raise ValueError("team does not survive a file round trip")


TeamTarget = tuple[Path, str]


def _team_targets(root: Path, teams: list) -> list[TeamTarget]:
    """Map every team to its Paydirt-style files; returns (path, text) for each file.

    Layout: ``<root>/<season>/<team-slug>/{offense,defense,special}.csv`` and ``team.yaml``,
    plus ``<root>/<season>/provenance/<team-slug>.csv`` kept outside the team folder. The slug
    is lowercase and hyphenated (``Miami (Florida)`` -> ``miami-florida``); the real name is
    stored in ``team.yaml``.
    """
    from bowl_bound.team_csv import (
        PROVENANCE_DIR,
        provenance_to_csv,
        team_folder_name,
        team_to_files,
        validate_team_name,
    )

    seen: set[tuple[int, str]] = set()
    targets: list[TeamTarget] = []
    for team in teams:
        season = team.chart.season
        if type(season) is not int or season < 1:
            raise ValueError("Team season must be a positive integer")
        validate_team_name(team.chart.name)
        slug = team_folder_name(team.chart.name)
        key = (season, slug)
        if key in seen:
            raise ValueError("Two teams map to the same season folder; refusing to merge them")
        seen.add(key)
        folder = root / str(season) / slug
        for filename, text in team_to_files(team.chart, team.metadata).items():
            targets.append((folder / filename, text))
        targets.append(
            (
                root / str(season) / PROVENANCE_DIR / f"{slug}.csv",
                provenance_to_csv(team.chart, team.metadata),
            )
        )
    return targets


def _write_teams(source: Path, root: Path, targets: list[TeamTarget], force: bool) -> None:
    """Write every file or none: a failure restores files already created or replaced."""
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        raise ValueError("Export root must be a directory, not a file or symlink")
    if root.resolve() == source.resolve():
        raise ValueError("Output must not replace the source PDF")
    for path, _ in targets:  # validate everything before the first write
        _validate_output(source, path, force)
    # Every directory this run may create, parents included, so a failure can remove them.
    candidates = {root}
    for path, _ in targets:
        candidates.update(p for p in path.parents if root in (p, *p.parents))
    created_dirs = [d for d in candidates if not d.exists()]
    done: list[tuple[Path, bytes | None]] = []
    try:
        for path, text in targets:
            previous = path.read_bytes() if path.exists() else None
            _write_report(source, path, text, force)
            done.append((path, previous))
    except BaseException:
        for path, previous in reversed(done):
            try:
                if previous is not None:
                    _write_report(source, path, previous, True)
                else:
                    path.unlink(missing_ok=True)
            except BaseException:
                # Continue best-effort rollback and preserve the original write error.
                pass
        for directory in sorted(created_dirs, key=lambda d: len(d.parts), reverse=True):
            try:
                directory.rmdir()
            except OSError:
                pass
        raise


def _summary(teams: list, targets: list[TeamTarget] | None = None) -> str:
    """Counts and destinations only: dry-run output must not echo chart contents."""
    from bowl_bound.team_csv import team_folder_name

    lines = ["status: validated", f"teams: {len(teams)}"]
    folders = set() if targets is None else {p.parent for p, _ in targets}
    for team in teams:
        chart = team.chart
        cells = sum(
            len(group)
            for group in (chart.offense, chart.supplemental, chart.defense, chart.special_teams)
        )
        lines.append(
            f"  {chart.name} {chart.season}: {cells} chart cells, "
            f"{len(chart.pat_outcomes)} PAT outcomes"
        )
        slug = team_folder_name(chart.name)
        for folder in sorted(folders, key=str):
            if folder.name == slug and folder.parent.name == str(chart.season):
                lines.append(f"    -> {folder}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Inspect or export a supported PDF; return 0 on success, 1 on document/I/O errors.

    Argument errors use argparse exit code 2. The default mode writes one inspection
    report to ``--output``. ``--export`` validates every chart cell and PAT outcome and
    writes Paydirt-style CSV files into ``<output>/<season>/<team>/``. All of it is private.
    """
    parser = argparse.ArgumentParser(description="Inspect or export Bowl Bound team PDFs")
    parser.add_argument("input", type=Path, help="PDF or directory containing exactly one PDF")
    parser.add_argument(
        "--output",
        "-o",
        required=True,
        type=Path,
        help="Private report file, or with --export the seasons root folder",
    )
    parser.add_argument("--export", action="store_true", help="Validate and export team data")
    parser.add_argument("--dry-run", action="store_true", help="Process without filesystem writes")
    parser.add_argument(
        "--force", action="store_true", help="Explicitly replace an existing output file"
    )
    arguments = parser.parse_args(argv)
    try:
        source = _source_path(arguments.input)
        output = arguments.output
        if arguments.export:
            teams = export_document(source)
            _verify_teams(teams)
            targets = _team_targets(output, teams)
            if arguments.dry_run:
                print(_summary(teams, targets), end="")
                return 0
            _write_teams(source, output, targets, arguments.force)
            print(
                f"Wrote {len(teams)} private validated team(s) as {len(targets)} files under "
                f"{output}."
            )
            return 0
        if not arguments.dry_run:
            _validate_output(source, output, arguments.force)
        inspection = inspect_document(source)
        report = {
            "report_version": 1,
            "status": "inspection_only",
            "source_sha256": inspection.source_sha256,
            "pages": [asdict(page) for page in inspection.pages],
        }
        rendered = json.dumps(report, indent=2) + "\n"
        if arguments.dry_run:
            print(rendered, end="")
            return 0
        _write_report(source, output, rendered, arguments.force)
        print("Wrote private inspection report; playable team export needs --export.")
        return 0
    except (OSError, ValueError, ImportInspectionError) as error:
        print(f"PDF import error: {error}", file=sys.stderr)
        return 1
    except Exception:  # noqa: BLE001 - a fixed message avoids leaking document text
        action = "exporting" if arguments.export else "inspecting"
        print(
            f"PDF import error: unexpected failure while {action} the document; "
            "the document may use an unsupported layout",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
