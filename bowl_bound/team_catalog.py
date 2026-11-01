"""Shared discovery and loading for installed local teams."""

import re
from dataclasses import dataclass
from pathlib import Path

from .models import TeamChart
from .team_csv import TeamFileMetadata, TeamFormatError, load_team, team_folder_name

TEAM_ID_MAX_LENGTH = 120
TEAM_ID_RE = re.compile(r"^[1-9][0-9]{0,5}/[a-z0-9]+(?:-[a-z0-9]+)*$")
_SEASON_RE = re.compile(r"^[1-9][0-9]{0,5}$")


class TeamCatalogError(ValueError):
    """Invalid, missing or unreadable local team information."""


class TeamNotFoundError(TeamCatalogError):
    """The canonical team folder does not exist."""


@dataclass(frozen=True)
class TeamEntry:
    """One readable local team and its canonical catalog identifier."""

    key: str
    name: str
    season: int


class TeamCatalog:
    """Discover and load canonical season/team folders without exposing chart data."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.problems: tuple[str, ...] = ()

    def load(self, key: str) -> TeamChart:
        """Load an exact team ID while rejecting traversal and symlinked team paths."""
        return self.load_with_metadata(key)[0]

    def load_with_metadata(self, key: str) -> tuple[TeamChart, TeamFileMetadata]:
        """Load a team and its rules privileges without exposing local file paths."""
        if type(key) is not str or len(key) > TEAM_ID_MAX_LENGTH or not TEAM_ID_RE.fullmatch(key):
            raise TeamCatalogError(
                "Team ID must be a canonical season/team, e.g. 2007/cedar-valley."
            )
        season, folder = key.split("/")
        directory = self.root / season
        team_directory = directory / folder
        if any(path.is_symlink() for path in (self.root, directory, team_directory)):
            raise TeamCatalogError("Team folders must not use symlinks.")
        if not team_directory.is_dir():
            raise TeamNotFoundError("Team folder does not exist.")
        try:
            chart, metadata = load_team(directory, folder)
        except (TeamFormatError, OSError) as error:
            raise TeamCatalogError("Team could not be read; check the local team files.") from error
        return chart, metadata

    def teams(self) -> tuple[TeamEntry, ...]:
        """List readable canonical teams and summarize unreadable entries safely."""
        if not self.root.is_dir() or self.root.is_symlink():
            raise TeamCatalogError("Seasons directory is missing or symlinked.")

        entries: list[TeamEntry] = []
        problems: list[str] = []
        for metadata in sorted(self.root.glob("*/*/team.yaml")):
            folder = metadata.parent
            season_directory = folder.parent
            if (
                not _SEASON_RE.fullmatch(season_directory.name)
                or folder.name == "provenance"
                or any(path.is_symlink() for path in (season_directory, folder, metadata))
            ):
                continue
            try:
                if team_folder_name(folder.name) != folder.name:
                    continue
            except TeamFormatError:
                continue
            key = f"{season_directory.name}/{folder.name}"
            if not TEAM_ID_RE.fullmatch(key):
                continue
            try:
                chart = self.load(key)
            except TeamCatalogError:
                problems.append(f"{key}: could not be read")
            else:
                entries.append(TeamEntry(key, chart.name, chart.season))

        self.problems = tuple(problems)
        return tuple(entries)
