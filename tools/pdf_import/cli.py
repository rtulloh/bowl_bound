"""Safe CLI boundary for the development-only PDF inspection pipeline."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bowl_bound.team_csv import team_folder_name  # noqa: E402 - engine codec, no PDF libraries

from .inspection import ImportInspectionError, inspect_document

if TYPE_CHECKING:  # the type only; importing .export at runtime would pull in the PDF libraries
    from .export import ExportedTeam


def export_document(path: Path) -> list:
    """Load the export pipeline lazily so inspection never needs it."""
    from .export import export_document as run_export

    return run_export(path)


def _sources(path: Path) -> list[Path]:
    """Return the PDFs to process: the one file given, or every PDF in a directory.

    Directory discovery is non-recursive, sorted by name, and ignores hidden files. A symlink
    among the candidates refuses the whole run before any PDF is processed.
    """
    if path.is_dir():
        candidates = sorted(
            entry
            for entry in path.iterdir()
            if entry.suffix.lower() == ".pdf" and not entry.name.startswith(".")
        )
        if any(entry.is_symlink() for entry in candidates):
            raise ValueError("Refusing a symlinked PDF in the input directory")
        files = [entry for entry in candidates if entry.is_file()]
        if not files:
            raise ValueError("Input directory contains no PDF files")
        return files
    if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".pdf":
        raise ValueError("Input must be an existing, non-symlink PDF or a directory of PDFs")
    return [path]


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
TeamIdentity = tuple[int, str]


@dataclass(frozen=True)
class PlannedPDF:
    """One validated PDF and all team identities and destinations it owns."""

    index: int
    source: Path
    teams: tuple[ExportedTeam, ...]
    targets: tuple[TeamTarget, ...]
    identities: frozenset[TeamIdentity]


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


def _write_teams(source: Path, root: Path, targets: Sequence[TeamTarget], force: bool) -> None:
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


def _summary(teams: Sequence[ExportedTeam], targets: Sequence[TeamTarget] | None = None) -> str:
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


def _failure_reason(error: Exception) -> str:
    """A one-line reason that never carries chart text, filenames, or local paths."""
    if isinstance(error, OSError):
        return error.strerror or "file operation failed"
    if isinstance(error, (ValueError, ImportInspectionError)):
        return str(error)
    return (
        "unexpected failure while exporting the document; "
        "the document may use an unsupported layout"
    )


def _run_batch(sources: list[Path], output: Path, force: bool, dry_run: bool) -> int:
    """Export every PDF; one PDF's failure never blocks the others.

    Phase 1 validates every PDF and checks for teams repeated across the batch, so a repeat
    is refused rather than merged. Phase 2 writes each PDF's files all-or-nothing; a failure
    there is reported and the other PDFs still run. Returns 0 only if every PDF succeeded.
    """
    total = len(sources)
    failures = 0
    plans: list[PlannedPDF] = []
    failures_by_index: dict[int, Exception] = {}
    owners: dict[TeamIdentity, set[int]] = {}
    for index, source in enumerate(sources, 1):
        try:
            teams = export_document(source)
            _verify_teams(teams)
            identities = frozenset(
                (team.chart.season, team_folder_name(team.chart.name)) for team in teams
            )
            for identity in identities:
                owners.setdefault(identity, set()).add(index)
            targets = _team_targets(output, teams)
            plans.append(PlannedPDF(index, source, tuple(teams), tuple(targets), identities))
        except Exception as error:  # noqa: BLE001 - reason is sanitized; document text never printed
            failures_by_index[index] = error

    colliding_indices = {
        index for indices in owners.values() if len(indices) > 1 for index in indices
    }
    for index in colliding_indices:
        failures_by_index[index] = ValueError(
            "a team in this PDF also appears in another PDF; refusing to merge either PDF"
        )
    for index, error in sorted(failures_by_index.items()):
        source = sources[index - 1]
        label = f"[{index}/{total}] {source.name}"
        print(f"{label}: FAILED - {_failure_reason(error)}", file=sys.stderr)

    planned = [plan for plan in plans if plan.index not in failures_by_index]
    failures = len(failures_by_index)
    if dry_run:
        for plan in planned:
            print(f"[{plan.index}/{total}] {plan.source.name}: ok (dry run)")
            print(_summary(plan.teams, plan.targets), end="")
        print(f"summary: {len(planned)} succeeded, {failures} failed")
        return 0 if failures == 0 else 1
    succeeded = 0
    for plan in planned:
        label = f"[{plan.index}/{total}] {plan.source.name}"
        try:
            _write_teams(plan.source, output, plan.targets, force)
            succeeded += 1
            print(f"{label}: ok")
        except Exception as error:  # noqa: BLE001 - reason is sanitized
            failures += 1
            print(f"{label}: FAILED - {_failure_reason(error)}", file=sys.stderr)
    print(f"summary: {succeeded} succeeded, {failures} failed")
    return 0 if failures == 0 else 1


def main(argv: list[str] | None = None) -> int:
    """Inspect or export a supported PDF; return 0 on success, 1 on document/I/O errors.

    Argument errors use argparse exit code 2. The default mode writes one inspection
    report to ``--output``. ``--export`` validates every chart cell and PAT outcome and
    writes Paydirt-style CSV files into ``<output>/<season>/<team>/``. All of it is private.
    """
    parser = argparse.ArgumentParser(description="Inspect or export Bowl Bound team PDFs")
    parser.add_argument("input", type=Path, help="A PDF, or a directory of PDFs")
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
        sources = _sources(arguments.input)
        output = arguments.output
        if arguments.export:
            return _run_batch(sources, output, arguments.force, arguments.dry_run)
        source = sources[0]
        if len(sources) != 1:
            raise ValueError("Inspection mode takes exactly one PDF; use --export for a directory")
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
