"""Safe CLI boundary for the development-only PDF inspection pipeline."""

from __future__ import annotations

import argparse
import errno
import json
import os
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .errors import ImportValidationError
from .inspection import ImportInspectionError, SafeImportInspectionError, inspect_document

if TYPE_CHECKING:  # the type only; importing .export at runtime would pull in the PDF libraries
    from .export import ExportedTeam


class SafeCLIError(ValueError):
    """A project-authored CLI validation failure safe to display as written."""


def export_document(path: Path) -> list:
    """Load the export pipeline lazily so inspection never needs it."""
    from .export import export_document as run_export

    return run_export(path)


def _sources(path: Path, *, allow_directory: bool) -> list[Path]:
    """Return input PDFs while enforcing inspection and export input contracts.

    Direct input symlinks are rejected before directory checks. Inspection requires one PDF;
    export may scan a directory non-recursively, sorted by name, ignoring hidden files.
    """
    if path.is_symlink():
        raise SafeCLIError("Input must not be a symlink")
    if path.is_dir():
        if not allow_directory:
            raise SafeCLIError(
                "Inspection mode requires a single PDF file; use --export for directory input"
            )
        candidates = sorted(
            (
                entry
                for entry in path.iterdir()
                if entry.suffix.lower() == ".pdf" and not entry.name.startswith(".")
            ),
            key=lambda entry: (entry.name.casefold(), entry.name),
        )
        if any(entry.is_symlink() for entry in candidates):
            raise SafeCLIError("Refusing a symlinked PDF in the input directory")
        files = [entry for entry in candidates if entry.is_file()]
        if not files:
            raise SafeCLIError("Input directory contains no PDF files")
        return files
    if not path.is_file() or path.suffix.lower() != ".pdf":
        if allow_directory:
            raise SafeCLIError("Input must be a non-symlink PDF or directory of PDFs")
        raise SafeCLIError("Inspection mode requires an existing, non-symlink PDF file")
    return [path]


def _refuse_symlinked_parents(output: Path) -> None:
    absolute = Path(os.path.abspath(output))
    for parent in absolute.parents:
        if parent.is_symlink() and parent != Path(parent.anchor):
            raise SafeCLIError("Refusing an output path that passes through a symlinked directory")


def _validate_output(source: Path, output: Path, force: bool) -> None:
    try:
        same_path = output.resolve() == source.resolve()
        same_file = output.exists() and os.path.samefile(source, output)
    except (OSError, RuntimeError) as error:
        raise SafeCLIError("Output path cannot be resolved safely") from error
    if same_path or same_file:
        raise SafeCLIError("Output must not replace the source PDF")
    if output.is_symlink():
        raise SafeCLIError("Refusing a symlink output path")
    _refuse_symlinked_parents(output)
    if output.exists() and not output.is_file():
        raise SafeCLIError("Output must be a file, not a directory")
    if output.exists() and not force:
        raise SafeCLIError("Output exists; pass --force to explicitly replace it")


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


TeamTarget = tuple[Path, str]
TeamIdentity = tuple[int, str]


@dataclass(frozen=True)
class PreparedTeam:
    """One team whose serialized files have passed the strict bundle round trip."""

    team: ExportedTeam
    identity: TeamIdentity
    files: tuple[tuple[str, str], ...]
    provenance_csv: str
    cell_count: int
    pat_count: int


@dataclass(frozen=True)
class PlannedPDF:
    """One PDF's validated export targets and user-safe summary."""

    targets: tuple[TeamTarget, ...]
    summary: str


@dataclass(frozen=True)
class PDFPlanResult:
    """Planning outcome for one source PDF, including identities found before failure."""

    index: int
    source: Path
    identities: frozenset[TeamIdentity]
    plan: PlannedPDF | None
    error: Exception | None


@dataclass(frozen=True)
class PDFResult:
    """Final per-PDF outcome used to report status and calculate the batch exit code."""

    index: int
    source: Path
    succeeded: bool
    error: Exception | None = None
    summary: str | None = None


def _verify_teams(teams: Sequence[ExportedTeam]) -> tuple[PreparedTeam, ...]:
    """Serialize and round-trip each team once, retaining verified content for export."""
    from bowl_bound.team_csv import (
        provenance_to_csv,
        team_folder_name,
        team_from_files,
        team_to_files,
        validate_team_name,
    )

    prepared: list[PreparedTeam] = []
    for team in teams:
        season = team.chart.season
        if type(season) is not int or season < 1:
            raise SafeCLIError("Team season must be a positive integer")
        validate_team_name(team.chart.name)
        identity = (season, team_folder_name(team.chart.name))
        files = team_to_files(team.chart, team.metadata)
        provenance_csv = provenance_to_csv(team.chart, team.metadata)
        decoded = team_from_files(files, provenance_csv)
        if decoded != (team.chart, team.metadata):
            raise SafeCLIError("team does not survive a file round trip")
        cell_count = sum(
            len(group)
            for group in (
                team.chart.offense,
                team.chart.supplemental,
                team.chart.defense,
                team.chart.special_teams,
            )
        )
        prepared.append(
            PreparedTeam(
                team,
                identity,
                tuple(files.items()),
                provenance_csv,
                cell_count,
                len(team.chart.pat_outcomes),
            )
        )
    return tuple(prepared)


def _team_targets(root: Path, teams: Sequence[PreparedTeam]) -> tuple[TeamTarget, ...]:
    """Map verified serialized files to destinations, rejecting intra-PDF collisions.

    Layout: ``<root>/<season>/<team-slug>/{offense,defense,special}.csv`` and ``team.yaml``,
    plus ``<root>/<season>/provenance/<team-slug>.csv`` kept outside the team folder. The slug
    is lowercase and hyphenated (``Miami (Florida)`` -> ``miami-florida``); the real name is
    stored in ``team.yaml``.
    """
    from bowl_bound.team_csv import PROVENANCE_DIR

    seen: set[TeamIdentity] = set()
    targets: list[TeamTarget] = []
    for prepared in teams:
        season, slug = prepared.identity
        if prepared.identity in seen:
            raise SafeCLIError("Two teams map to the same season folder; refusing to merge them")
        seen.add(prepared.identity)
        folder = root / str(season) / slug
        for filename, text in prepared.files:
            targets.append((folder / filename, text))
        targets.append(
            (
                root / str(season) / PROVENANCE_DIR / f"{slug}.csv",
                prepared.provenance_csv,
            )
        )
    return tuple(targets)


def _preflight_teams(source: Path, root: Path, targets: Sequence[TeamTarget], force: bool) -> None:
    """Validate every batch destination without creating directories or writing files."""
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        raise SafeCLIError("Export root must be a directory, not a file or symlink")
    if root.resolve() == source.resolve():
        raise SafeCLIError("Output must not replace the source PDF")
    for path, _ in targets:
        _validate_output(source, path, force)


def _write_teams(source: Path, root: Path, targets: Sequence[TeamTarget], force: bool) -> None:
    """Write every file or none: a failure restores files already created or replaced."""
    _preflight_teams(source, root, targets, force)
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


def _summary(teams: Sequence[PreparedTeam], root: Path) -> str:
    """Counts and destinations only: dry-run output must not echo chart contents."""
    lines = ["status: validated", f"teams: {len(teams)}"]
    for prepared in teams:
        chart = prepared.team.chart
        lines.append(
            f"  {chart.name} {chart.season}: {prepared.cell_count} chart cells, "
            f"{prepared.pat_count} PAT outcomes"
        )
        lines.append(f"    -> {root / str(chart.season) / prepared.identity[1]}")
    return "\n".join(lines) + "\n"


_SAFE_OS_ERROR_MESSAGES = {
    errno.EACCES: "Permission denied",
    errno.EPERM: "Permission denied",
    errno.EEXIST: "Output already exists",
    errno.ENOENT: "No such file or directory",
    errno.ENOTDIR: "A path component is not a directory",
    errno.EISDIR: "Output path is a directory",
    errno.ENOSPC: "No space left on device",
}


def _failure_reason(error: Exception, action: str = "exporting") -> str:
    """Return project-authored text only; never echo arbitrary exception details."""
    if isinstance(error, SafeCLIError):
        return str(error)
    if isinstance(error, SafeImportInspectionError):
        return str(error)
    if isinstance(error, ImportValidationError):
        return str(error)
    if isinstance(error, ImportInspectionError):
        return "PDF could not be inspected; it may be malformed, encrypted, or unsupported"
    if isinstance(error, OSError):
        return _SAFE_OS_ERROR_MESSAGES.get(error.errno, "File operation failed")
    return (
        f"unexpected failure while {action} the document; "
        "the document may use an unsupported layout"
    )


def _run_batch(sources: list[Path], output: Path, force: bool, dry_run: bool) -> int:
    """Export every PDF; one PDF's failure never blocks the others.

    Phase 1 validates every PDF and checks for teams repeated across the batch, so a repeat
    is refused rather than merged. Phase 2 writes each PDF's files all-or-nothing; a failure
    there is reported and the other PDFs still run. Returns 0 only if every PDF succeeded.
    """
    plan_results: list[PDFPlanResult] = []
    for index, source in enumerate(sources, 1):
        identities: frozenset[TeamIdentity] = frozenset()
        plan: PlannedPDF | None = None
        error: Exception | None = None
        try:
            teams = _verify_teams(export_document(source))
            identities = frozenset(team.identity for team in teams)
            targets = _team_targets(output, teams)
            _preflight_teams(source, output, targets, force)
            summary = _summary(teams, output)
            plan = PlannedPDF(targets, summary)
        except Exception as caught:  # noqa: BLE001 - reason is sanitized at the CLI boundary
            error = caught
        plan_results.append(PDFPlanResult(index, source, identities, plan, error))

    owners: dict[TeamIdentity, set[Path]] = {}
    for item in plan_results:
        for identity in item.identities:
            owners.setdefault(identity, set()).add(item.source)
    colliding_sources = {
        source
        for sources_with_identity in owners.values()
        if len(sources_with_identity) > 1
        for source in sources_with_identity
    }
    results: list[PDFResult] = []
    total = len(plan_results)
    for item in plan_results:
        label = f"[{item.index}/{total}] {item.source.name}"
        error = item.error
        if item.source in colliding_sources:
            error = SafeCLIError(
                "a team in this PDF also appears in another PDF; refusing to merge either PDF"
            )
        if error is not None:
            result = PDFResult(item.index, item.source, False, error)
        elif item.plan is None:
            result = PDFResult(
                item.index,
                item.source,
                False,
                RuntimeError("batch planning produced no result"),
            )
        elif dry_run:
            result = PDFResult(item.index, item.source, True, summary=item.plan.summary)
        else:
            try:
                _write_teams(item.source, output, item.plan.targets, force)
                result = PDFResult(item.index, item.source, True)
            except Exception as caught:  # noqa: BLE001 - reason is sanitized at the CLI boundary
                result = PDFResult(item.index, item.source, False, caught)
        results.append(result)

        if result.succeeded:
            suffix = " (dry run)" if dry_run else ""
            print(f"{label}: ok{suffix}")
            if result.summary is not None:
                print(result.summary, end="")
        else:
            failure = result.error or RuntimeError("batch item failed without a reason")
            print(f"{label}: FAILED - {_failure_reason(failure)}", file=sys.stderr)

    succeeded = sum(result.succeeded for result in results)
    failures = len(results) - succeeded
    print(f"summary: {succeeded} succeeded, {failures} failed")
    return 0 if failures == 0 else 1


def main(argv: list[str] | None = None) -> int:
    """Inspect one PDF or export charts from a PDF or directory.

    Argument errors use argparse exit code 2. The default mode writes one inspection
    report to ``--output`` and requires one PDF file. ``--export`` accepts a PDF or directory,
    validates every chart cell and PAT outcome, and writes private CSV files.
    """
    parser = argparse.ArgumentParser(description="Inspect or export Bowl Bound team PDFs")
    parser.add_argument(
        "input", type=Path, help="A PDF; with --export, a directory of PDFs is also accepted"
    )
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
        sources = _sources(arguments.input, allow_directory=arguments.export)
        output = arguments.output
        if arguments.export:
            return _run_batch(sources, output, arguments.force, arguments.dry_run)
        source = sources[0]
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
    except Exception as error:  # noqa: BLE001 - sanitize every failure at the CLI boundary
        action = "exporting" if arguments.export else "inspecting"
        print(
            f"PDF import error: {_failure_reason(error, action)}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
